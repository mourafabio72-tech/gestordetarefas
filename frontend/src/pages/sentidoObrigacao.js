// "O documento vai para que lado?" da tela de Obrigação.
//
// Fica em arquivo próprio, sem JSX, no molde de payloadObrigacao.js, para rodar
// numa prova em Node puro (frontend/provas/prova_sentido_obrigacao.js).
//
// A regra do documento é do SERVIDOR (`perfil_documento`, backend/app/models.py).
// Aqui ela só é espelhada para a tela mostrar o que vai acontecer, e a prova
// confere o espelho contra uma tabela escrita à mão.

/** As quatro opções, na ordem da tela. A dica vai no `title` do botão. */
export const SENTIDOS = [
  {
    valor: 'receber',
    rotulo: 'Receber do cliente',
    dica: 'O cliente envia o comprovante e a tarefa baixa pelo e-validador.',
  },
  {
    valor: 'entregar',
    rotulo: 'Entregar ao cliente',
    dica: 'Guia, boleto ou relatório. Anexar e enviar conclui a tarefa.',
  },
  {
    valor: 'transmitir',
    rotulo: 'Transmitir ao órgão',
    dica: 'Obrigação acessória que o escritório transmite (SPED, DCTFWeb, EFD). '
      + 'A baixa é pelo recibo no e-validador, e o recibo fica no acervo.',
  },
  {
    valor: 'interna',
    rotulo: 'Nenhum, tarefa interna',
    dica: 'Conciliar banco, lançar notas, fechar balancete. Baixa na mão, '
      + 'ou pelo e-validador se você marcar "Exige documento".',
  },
];

/** Sentido nulo ou vazio (obrigação antiga) se comporta como receber, igual ao servidor. */
export function sentidoDoForm(form) {
  return (form && form.sentido) || 'receber';
}

/**
 * Os identificadores são o que o e-validador procura no documento. Aparecem
 * para receber, transmitir e entregar (a guia de imposto casa pelo código
 * dela, 2026-09-19), e para a interna que exige documento: sem eles, essa
 * interna trava a baixa manual e nunca casa com o comprovante.
 */
export function mostraIdentificadores(form) {
  const sentido = sentidoDoForm(form);
  if (sentido === 'interna') return form.exige_documento === true;
  return true;
}

/** O "Exige documento" marcado, pela mesma regra de `perfil_documento`. */
export function exigeDocumentoMarcado(form) {
  const f = form || {};
  if (f.exige_documento === true || f.exige_documento === false) return f.exige_documento;
  if (sentidoDoForm(f) === 'interna') return false;
  return !!(f.identificadores || '').trim();
}
