// O que a faixa de conferência da janela de envio diz. Separado do Tarefas.jsx
// para a prova rodar em Node.
//
// Até 2026-10-27 bastava "nada contradiz e leu algo" para dizer "CNPJ e
// competência batem", e a guia de ISS em imagem só tinha o CNPJ lido. Agora a
// faixa diz o que foi lido de fato, e o que falta conferir a olho.

export function textoConferencia(conf) {
  if (!conf) return null;
  if (!conf.ok) return { tipo: 'contradiz', texto: '' };
  if (!conf.leu_algo) {
    return { tipo: 'nada', texto: 'Não consegui ler CNPJ nem competência neste arquivo (escaneado ou sem texto). Confira você antes de enviar.' };
  }
  if (conf.cnpj_lido && conf.competencia_lida) {
    return { tipo: 'ok', texto: '✓ O documento confere: CNPJ e competência batem com a tarefa.' };
  }
  if (conf.cnpj_lido) {
    return { tipo: 'parcial', texto: 'O CNPJ confere com a tarefa. A competência não foi lida no documento: confira o mês na guia antes de enviar.' };
  }
  return { tipo: 'parcial', texto: 'A competência confere com a tarefa. O CNPJ não foi lido no documento: confira a empresa na guia antes de enviar.' };
}
