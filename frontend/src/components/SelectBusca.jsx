import { useEffect, useRef, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { filtrarOpcoes } from '../pages/desvincularEmpresa.js';

/**
 * Escolha única com busca, no lugar do `<select>` nativo (Sem_Select_Nativo).
 *
 * `opcoes` é `[{ valor, rotulo }]`. O painel abre ABAIXO do botão, posicionado
 * dentro do próprio componente: quem o usa num modal não pode pôr `overflow`
 * no caminho, senão o painel é cortado na borda (o problema que a nota
 * Padrao_Modal_Popup_Centrado resolve com `overflow:visible`). No Desvincular
 * a rolagem fica só na lista de obrigações, e a caixa do modal não corta nada.
 */
export default function SelectBusca({
  id, opcoes, valor, onChange, placeholder = 'Selecione',
  desabilitado = false, vazio = 'Nada com esse nome.',
}) {
  const [aberto, setAberto] = useState(false);
  const [busca, setBusca] = useState('');
  const caixa = useRef(null);
  const campoBusca = useRef(null);

  const escolhida = (opcoes || []).find((o) => o.valor === valor);
  const visiveis = filtrarOpcoes(opcoes, busca);

  useEffect(() => {
    if (!aberto) return undefined;
    campoBusca.current?.focus();
    const fora = (e) => { if (caixa.current && !caixa.current.contains(e.target)) setAberto(false); };
    document.addEventListener('mousedown', fora);
    return () => document.removeEventListener('mousedown', fora);
  }, [aberto]);

  const escolher = (o) => {
    onChange(o.valor);
    setAberto(false);
    setBusca('');
  };

  const teclas = (e) => {
    if (e.key === 'Escape') { e.stopPropagation(); setAberto(false); }
    if (e.key === 'Enter' && visiveis.length) { e.preventDefault(); escolher(visiveis[0]); }
  };

  return (
    <div ref={caixa} className="relative">
      <button
        id={id}
        type="button"
        disabled={desabilitado}
        aria-haspopup="listbox"
        aria-expanded={aberto}
        onClick={() => setAberto((a) => !a)}
        className="input-field flex items-center justify-between gap-2 text-left disabled:opacity-50"
      >
        <span className={`truncate ${escolhida ? 'text-gray-800' : 'text-gray-400'}`}>
          {escolhida ? escolhida.rotulo : placeholder}
        </span>
        <ChevronDown size={16} className="shrink-0 text-gray-400" />
      </button>
      {aberto && (
        <div className="absolute left-0 right-0 top-full z-20 mt-1 rounded-lg border border-gray-200 bg-white shadow-lg">
          <input
            ref={campoBusca}
            type="text"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            onKeyDown={teclas}
            placeholder="Buscar..."
            aria-label="Buscar"
            className="w-full rounded-t-lg border-b border-gray-200 px-3 py-2 text-sm outline-none"
          />
          <div role="listbox" className="max-h-64 overflow-y-auto py-1">
            {visiveis.length === 0 && (
              <p className="px-3 py-2 text-sm text-gray-400">{vazio}</p>
            )}
            {visiveis.map((o) => (
              <button
                key={o.valor}
                type="button"
                role="option"
                aria-selected={o.valor === valor}
                onClick={() => escolher(o)}
                className={`block w-full truncate px-3 py-1.5 text-left text-sm hover:bg-primary-50 hover:text-primary-800 ${
                  o.valor === valor ? 'bg-primary-50 font-medium text-primary-800' : 'text-gray-700'}`}
              >
                {o.rotulo}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
