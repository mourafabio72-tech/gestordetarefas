// Uniformiza a razão social na exibição — NÃO mexe no cadastro.
//
// O cadastro vem de origens diferentes (digitado à mão, importado da Receita,
// colado de planilha) e chega misturado: "Mark Building Gerenc. Predial Ltda."
// ao lado de "RIO BRAVO COM. DE ARMAS MUNIÇÕES E ACESS. LTDA". Empilhados como
// cabeçalho de seção, o caixa-alta grita e o outro sussurra. O padrão adotado é
// o da MKB: Caixa de Título, preposição em minúscula, abreviação com ponto.
//
// Sem JSX e sem React, como os vizinhos, para provar em Node puro.

/** Vão em minúscula quando não são a primeira palavra. */
const ATONAS = new Set(['de', 'da', 'do', 'das', 'dos', 'e', 'em', 'a', 'o', 'as', 'os', 'à', 'às']);

/**
 * Siglas e formas jurídicas que têm grafia própria.
 *
 * A lista existe porque nenhuma regra automática separa sigla de palavra:
 * "MKB" e "RIO" têm três letras cada, e só quem conhece o cliente sabe que a
 * primeira é sigla. Cliente novo cuja sigla não esteja aqui sai em Caixa de
 * Título ("Iwc" em vez de "IWC") — o conserto é acrescentar a chave abaixo.
 */
const SIGLAS = {
  LTDA: 'Ltda', ME: 'ME', EPP: 'EPP', EIRELI: 'Eireli', MEI: 'MEI',
  SA: 'S.A.', 'S/A': 'S.A.', 'S.A': 'S.A.', CIA: 'Cia', JR: 'Jr',
  MKB: 'MKB', IWC: 'IWC', BPS4: 'BPS4', CW: 'CW', SPE: 'SPE',
};

/** Sem vogal e curta: CW, MKB, BPS. Pega sigla que não está na lista fixa. */
function pareceSigla(bruto) {
  const so = bruto.replace(/[^A-Za-zÀ-ÿ0-9]/g, '');
  if (!so || so.length > 4) return false;
  if (/\d/.test(so)) return true;                       // BPS4, 3M
  return !/[AEIOUÀ-ÿaeiou]/.test(so);                   // CW, MKB, JBS
}

/** Um pedaço de palavra (entre espaço, hífen ou barra). */
function pedaco(bruto, primeiro) {
  const nu = bruto.replace(/[.,]+$/, '');               // "COM." -> "COM"
  const pontuacao = bruto.slice(nu.length);
  const chave = nu.toUpperCase();

  if (SIGLAS[chave]) return SIGLAS[chave] + pontuacao;
  // Abreviação (terminou em ponto) é palavra encurtada, nunca sigla: "Com.".
  if (!pontuacao && pareceSigla(nu)) return chave + pontuacao;
  const baixo = nu.toLocaleLowerCase('pt-BR');
  if (!primeiro && ATONAS.has(baixo)) return baixo + pontuacao;
  return baixo.charAt(0).toLocaleUpperCase('pt-BR') + baixo.slice(1) + pontuacao;
}

/**
 * Devolve a razão social pronta para exibir.
 *
 * Nome que JÁ tem minúscula é devolvido intacto (só com os espaços sobrando
 * aparados): quem cadastrou "Mark Building Gerenc. Predial Ltda." escreveu do
 * jeito que quer ver, e reprocessar só arriscaria estragar.
 */
export function formatarRazaoSocial(nome) {
  const texto = (nome || '').trim().replace(/\s+/g, ' ');
  if (!texto) return '';
  if (/[a-zà-ÿ]/.test(texto)) return texto;

  return texto.split(' ').map((palavra, i) => {
    let primeiro = i === 0;
    // A palavra inteira vem antes da repartição: "S/A" está no mapa e não pode
    // ser quebrada na barra, senão viraria "S" + "/" + "a".
    const inteira = palavra.replace(/[.,]+$/, '').toUpperCase();
    if (SIGLAS[inteira]) return SIGLAS[inteira];
    // Reparte em hífen e barra mantendo o separador: "LTDA-ME" -> "Ltda-ME".
    return palavra.split(/([-/])/).map((parte) => {
      if (parte === '-' || parte === '/') return parte;
      const saida = pedaco(parte, primeiro);
      primeiro = false;
      return saida;
    }).join('');
  }).join(' ');
}
