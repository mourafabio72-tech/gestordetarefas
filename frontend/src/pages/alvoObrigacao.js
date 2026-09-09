/**
 * Quem a obrigação alcança: o check "aplicar a todas", o perfil e as empresas
 * vinculadas, num lugar só.
 *
 * Isto morava espalhado no JSX, e o resultado era uma tela que dizia o
 * contrário do que fazia:
 *
 * · o check era DERIVADO de `!aplica_regimes && !aplica_segmentos`, então ficava
 *   marcado mesmo com dez empresas vinculadas em "somente estas";
 * · desmarcar o check FORÇAVA o primeiro regime da lista, então não havia
 *   caminho por ali para "só estas empresas": isso morava no `alvo_modo`, que a
 *   tela quase não mostrava.
 *
 * A lógica vem para cá para rodar em prova Node pura, pelo mesmo motivo de
 * `filtroTarefas.js` e `seletorResponsaveis.js`.
 */

/** O estado inicial, lido de uma obrigação que veio do servidor. */
export function estadoDoAlvo(form) {
  const f = form || {};
  return {
    form: f,
    // O check é ESTADO da tela, e não uma dedução: a pessoa pode desmarcar
    // "aplicar a todas" e ainda não ter escolhido nenhum regime.
    restringe: Boolean((f.aplica_regimes || '').trim() || (f.aplica_segmentos || '').trim()),
    // Para onde voltar se a última empresa vinculada for desmarcada.
    anterior: null,
  };
}

export function aplicaTodas(estado) {
  return !estado.restringe && (estado.form.alvo_modo || 'regra') !== 'vinculadas';
}

function comForm(estado, mudancas) {
  return { ...estado, form: { ...estado.form, ...mudancas } };
}

function guardar(estado) {
  // Guarda uma vez só: a segunda empresa vinculada não pode sobrescrever o
  // estado anterior com o que a primeira já tinha mudado.
  if (estado.anterior) return estado.anterior;
  return {
    alvo_modo: estado.form.alvo_modo || 'regra',
    aplica_regimes: estado.form.aplica_regimes || '',
    aplica_segmentos: estado.form.aplica_segmentos || '',
    restringe: estado.restringe,
  };
}

export function reduzirAlvo(estado, evento) {
  const e = estado;
  const ids = e.form.empresa_ids || [];

  switch (evento.tipo) {
    case 'vincular': {
      if (ids.includes(evento.id)) return e;
      const novos = [...ids, evento.id];
      // A PRIMEIRA empresa vinculada é a que muda o alvo: a partir daqui a
      // obrigação é de clientes escolhidos, e dizer "todas" seria mentira.
      if (ids.length === 0) {
        return {
          ...comForm(e, { empresa_ids: novos, alvo_modo: 'vinculadas' }),
          restringe: false,
          anterior: guardar(e),
        };
      }
      return comForm(e, { empresa_ids: novos });
    }

    case 'desvincular': {
      const novos = ids.filter((x) => x !== evento.id);
      if (novos.length > 0) return comForm(e, { empresa_ids: novos });
      // Desvinculou a última: volta ao que era. Ficar em "somente estas" com a
      // lista vazia é uma obrigação que não gera para ninguém, em silêncio.
      const volta = e.anterior || { alvo_modo: 'regra', aplica_regimes: '',
                                    aplica_segmentos: '', restringe: false };
      return {
        ...comForm(e, {
          empresa_ids: [],
          alvo_modo: volta.alvo_modo,
          aplica_regimes: volta.aplica_regimes,
          aplica_segmentos: volta.aplica_segmentos,
        }),
        restringe: volta.restringe,
        anterior: null,
      };
    }

    case 'vincular-varias': {
      const novos = [...new Set([...ids, ...(evento.ids || [])])];
      if (novos.length === ids.length) return e;
      if (ids.length === 0) {
        return {
          ...comForm(e, { empresa_ids: novos, alvo_modo: 'vinculadas' }),
          restringe: false,
          anterior: guardar(e),
        };
      }
      return comForm(e, { empresa_ids: novos });
    }

    case 'limpar-empresas':
      return reduzirAlvo(
        { ...e, form: { ...e.form, empresa_ids: ids.slice(0, 1) } },
        { tipo: 'desvincular', id: ids[0] }
      );

    case 'aplicar-todas':
      // Marcar limpa o perfil. DESmarcar não escolhe nada por você: antes ele
      // forçava o primeiro regime da lista, e a obrigação passava a valer para
      // um perfil que ninguém tinha pedido.
      return evento.valor
        ? { ...comForm(e, { aplica_regimes: '', aplica_segmentos: '' }), restringe: false }
        : { ...e, restringe: true };

    case 'modo': {
      if (evento.valor === 'vinculadas') {
        return { ...comForm(e, { alvo_modo: 'vinculadas' }), anterior: guardar(e) };
      }
      return comForm(e, { alvo_modo: 'regra' });
    }

    default:
      return e;
  }
}

/** O que a tela diz que está acontecendo, em uma frase. */
export function aviso(estado) {
  const f = estado.form;
  const n = (f.empresa_ids || []).length;
  if ((f.alvo_modo || 'regra') === 'vinculadas') {
    if (n === 0) {
      return 'Nenhuma empresa marcada: assim a obrigação não gera para ninguém.';
    }
    return `Somente ${n} empresa(s) recebem esta obrigação. Regime e segmento são ignorados.`;
  }
  if (estado.restringe) {
    const semEscolha = !(f.aplica_regimes || '').trim() && !(f.aplica_segmentos || '').trim();
    return semEscolha
      ? 'Escolha ao menos um regime ou segmento, senão a obrigação continua alcançando todas.'
      : 'A obrigação alcança quem casa com o perfil, mais as empresas vinculadas.';
  }
  return 'A obrigação alcança todas as empresas.';
}
