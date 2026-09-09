import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Users, X } from 'lucide-react';
import {
  alternar, elegiveis, escolhidos, filtrar, resumo,
} from '../pages/seletorResponsaveis';

/**
 * Escolher quem responde por alguma coisa. Duas apresentações, uma lógica.
 *
 * `modo="inline"`  a caixa com rolagem que a tela de Tarefas já usava.
 * `modo="popover"` o botão com os escolhidos em chip, que abre a lista. É o da
 *                  linha do setor no cadastro de empresa, onde uma caixa por
 *                  linha empilharia dez caixas roláveis na mesma tela.
 *
 * O popover é desenhado em `createPortal` no body, e não dentro do modal. O
 * modal de cadastro tem `overflow-y-auto`, e um filho posicionado dentro dele
 * seria CORTADO na borda, que é o mesmo problema que a nota
 * `Padrao_Modal_Popup_Centrado` resolve com `overflow:visible` no `<dialog>`.
 * Aqui a saída equivalente é sair do fluxo do modal.
 */
export default function SeletorResponsaveis({
  usuarios,
  valor,
  onChange,
  modo = 'inline',
  chave,
  aberto = false,
  onAbrir,
  onFechar,
  busca = '',
  onBuscar,
  desabilitado = false,
  vazio = 'sem responsável',
}) {
  const ids = valor || [];
  const pessoas = elegiveis(usuarios);
  const visiveis = filtrar(pessoas, modo === 'popover' ? busca : '', ids);

  const marcar = (id) => onChange(alternar(ids, id));

  const lista = (
    <div className="space-y-1">
      {visiveis.length === 0 && (
        <p className="text-xs text-gray-400 px-1 py-2">Ninguém com esse nome.</p>
      )}
      {visiveis.map((u) => (
        <label key={u.id} className="flex items-center gap-2 text-sm cursor-pointer px-1 py-0.5 rounded hover:bg-gray-50">
          <input
            type="checkbox"
            className="check-app"
            checked={ids.includes(u.id)}
            disabled={desabilitado}
            onChange={() => marcar(u.id)}
          />
          <span className="truncate">{u.nome}</span>
          {ids[0] === u.id && (
            <span className="ml-auto text-[10px] uppercase tracking-wide text-primary-600" title="Recebe a tarefa como responsável principal, e é dele que sai o supervisor">
              principal
            </span>
          )}
        </label>
      ))}
    </div>
  );

  if (modo === 'inline') {
    return (
      <>
        <div className="max-h-32 overflow-y-auto border border-gray-200 rounded-lg p-2">
          {lista}
        </div>
        <p className="text-xs text-gray-400 mt-1">{ids.length} selecionado(s)</p>
      </>
    );
  }

  return (
    <PopoverResponsaveis
      chave={chave}
      aberto={aberto}
      onAbrir={onAbrir}
      onFechar={onFechar}
      busca={busca}
      onBuscar={onBuscar}
      desabilitado={desabilitado}
      vazio={vazio}
      ids={ids}
      pessoas={pessoas}
      onChange={onChange}
      lista={lista}
    />
  );
}

function PopoverResponsaveis({
  chave, aberto, onAbrir, onFechar, busca, onBuscar, desabilitado, vazio,
  ids, pessoas, onChange, lista,
}) {
  const botao = useRef(null);
  const painel = useRef(null);
  const [caixa, setCaixa] = useState(null);

  // Setor que deixa de ser atendido fecha o popover dele. Sem isto, a lista
  // continua aberta e clicável sobre um setor que o submit vai descartar: a
  // tela mostraria uma escolha que não vai a lugar nenhum.
  useEffect(() => {
    if (desabilitado && aberto) onFechar();
  }, [desabilitado, aberto, onFechar]);

  // Posição vem do botão, e é refeita ao rolar ou redimensionar: o conteúdo do
  // modal rola, e um painel parado no lugar antigo fica solto na tela.
  useEffect(() => {
    if (!aberto) { setCaixa(null); return undefined; }
    const medir = () => {
      const r = botao.current?.getBoundingClientRect();
      if (r) setCaixa({ topo: r.bottom + 4, esquerda: r.left, largura: Math.max(r.width, 260) });
    };
    medir();
    window.addEventListener('scroll', medir, true);
    window.addEventListener('resize', medir);
    return () => {
      window.removeEventListener('scroll', medir, true);
      window.removeEventListener('resize', medir);
    };
  }, [aberto]);

  // ESC e clique fora fecham o POPOVER, e só ele. O modal de cadastro sai pelo
  // X ou pelo Cancelar, e por mais nada (`Padrao_Modal_Nao_Fecha_Sozinho`), por
  // isso o ESC é engolido aqui em vez de subir.
  useEffect(() => {
    if (!aberto) return undefined;
    const tecla = (e) => {
      if (e.key !== 'Escape') return;
      e.preventDefault();
      e.stopPropagation();
      onFechar();
    };
    const clique = (e) => {
      if (painel.current?.contains(e.target) || botao.current?.contains(e.target)) return;
      onFechar();
    };
    document.addEventListener('keydown', tecla, true);
    document.addEventListener('mousedown', clique, true);
    return () => {
      document.removeEventListener('keydown', tecla, true);
      document.removeEventListener('mousedown', clique, true);
    };
  }, [aberto, onFechar]);

  const marcados = escolhidos(ids, pessoas);

  return (
    <>
      <button
        type="button"
        ref={botao}
        disabled={desabilitado}
        onClick={() => onAbrir(chave)}
        className="flex-1 min-w-0 flex items-center gap-1.5 text-left px-3 py-1.5 border border-gray-300 rounded-lg bg-white hover:border-primary-400 disabled:bg-gray-50 disabled:text-gray-400 disabled:hover:border-gray-300"
      >
        {marcados.length === 0 ? (
          <span className="text-sm text-gray-400 truncate">{vazio}</span>
        ) : (
          <span className="flex flex-wrap gap-1 min-w-0">
            {marcados.map((u, i) => (
              <span
                key={u.id}
                title={i === 0 ? 'Responsável principal: é dele que sai o supervisor' : u.nome}
                className={`inline-flex items-center gap-1 text-[11px] px-1.5 py-0.5 rounded-full border ${
                  i === 0
                    ? 'bg-primary-50 border-primary-200 text-primary-700'
                    : 'bg-gray-50 border-gray-200 text-gray-600'
                }`}
              >
                {u.nome}
              </span>
            ))}
          </span>
        )}
        <Users className="w-3.5 h-3.5 ml-auto shrink-0 text-gray-400" />
      </button>

      {aberto && caixa && createPortal(
        <div
          ref={painel}
          style={{ top: caixa.topo, left: caixa.esquerda, width: caixa.largura }}
          className="fixed z-[60] bg-white border border-gray-200 rounded-lg shadow-lg p-2"
        >
          <div className="flex items-center gap-2 mb-2">
            <input
              autoFocus
              value={busca}
              onChange={(e) => onBuscar(e.target.value)}
              placeholder="Buscar pessoa"
              className="input-field py-1 text-sm"
            />
            <button type="button" onClick={onFechar} title="Fechar" className="text-gray-400 hover:text-gray-600">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="max-h-56 overflow-y-auto">{lista}</div>
          <p className="text-xs text-gray-400 mt-2 px-1">
            {ids.length} selecionado(s). O primeiro é o principal.
          </p>
          {ids.length > 0 && (
            <button
              type="button"
              onClick={() => onChange([])}
              className="text-xs text-gray-500 hover:text-gray-700 px-1 mt-1"
            >
              Limpar
            </button>
          )}
        </div>,
        document.body
      )}
    </>
  );
}
