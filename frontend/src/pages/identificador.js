// Conferência do identificador contra o texto do documento.
//
// Sem JSX e sem React, como os vizinhos, para provar em Node puro.
//
// Existe porque o modo de errar aqui é silencioso e caro: o identificador é
// procurado DENTRO do documento, e quem digita uma descrição — "planilha de
// apuração de IRPJ" — grava um texto que não existe em lugar nenhum. Nada
// falha na hora. O e-validador simplesmente nunca reconhece aquele documento,
// e a descoberta vem meses depois, quando alguém pergunta por que a baixa
// automática não funciona.

/** minúsculo, sem acento e com espaços colapsados — o mesmo que o backend faz. */
export function normalizar(texto) {
  return (texto || '')
    .normalize('NFKD').replace(/[̀-ͯ]/g, '')
    .toLowerCase().replace(/\s+/g, ' ').trim();
}

/**
 * O identificador aparece no documento?
 *
 * Devolve `{ estado, aviso }`. Estados:
 *   'vazio'      — nada digitado ainda
 *   'sem_texto'  — não há texto extraído para conferir (PDF escaneado)
 *   'achou'      — está no documento
 *   'nao_achou'  — NÃO está, e é isso que precisa gritar
 *   'curto'      — existe, mas é curto demais para distinguir
 */
export function conferirIdentificador(identificador, textoDocumento) {
  const alvo = normalizar(identificador);
  if (!alvo) return { estado: 'vazio', aviso: null };

  const texto = normalizar(textoDocumento);
  if (!texto) {
    return { estado: 'sem_texto',
             aviso: 'Não consegui ler o texto deste arquivo, então não dá para conferir. '
                  + 'Certifique-se de que o trecho existe mesmo no documento.' };
  }
  if (!texto.includes(alvo)) {
    return { estado: 'nao_achou',
             aviso: 'Este texto NÃO aparece no documento. O identificador é procurado '
                  + 'dentro do arquivo — se ele não estiver lá, o e-validador nunca vai '
                  + 'reconhecer este tipo de documento. Copie um título ou cabeçalho que '
                  + 'esteja escrito no arquivo.' };
  }
  // Três letras casam com meio mundo; o matcher fica ambíguo e ninguém percebe.
  if (alvo.length < 4) {
    return { estado: 'curto',
             aviso: 'Muito curto: vai casar com documentos que não são deste tipo.' };
  }
  return { estado: 'achou', aviso: null };
}
