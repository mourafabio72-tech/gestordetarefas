import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { obrigacoesAPI } from '../services/api';
import { mensagemDeErro } from '../services/erroApi';
import { UserX, Loader2 } from 'lucide-react';

// Empresas que uma obrigação de envio alcança e que não têm para onde enviar.
// Mostra antes o que o e-validador só descobriria com a guia na mão (2026-11-03).
export default function ClientesSemContato() {
  const [linhas, setLinhas] = useState(null);
  const [erro, setErro] = useState('');
  const [busca, setBusca] = useState('');

  useEffect(() => {
    obrigacoesAPI.semContato()
      .then((r) => setLinhas(r.data))
      .catch((e) => setErro(mensagemDeErro(e, 'Não foi possível carregar o relatório.')));
  }, []);

  const lista = useMemo(() => {
    const q = busca.trim().toLowerCase();
    if (!q) return linhas || [];
    return (linhas || []).filter((l) =>
      `${l.razao_social} ${l.cnpj || ''} ${l.obrigacoes.join(' ')}`.toLowerCase().includes(q));
  }, [linhas, busca]);

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <UserX className="text-primary-700" />
        <h1 className="text-2xl font-bold text-gray-800">Clientes sem contato</h1>
      </div>
      <p className="text-sm text-gray-600 mb-4">
        Empresas alcançadas por uma obrigação de envio ao cliente, sem e-mail ou telefone válido na ficha
        e sem usuário do tipo cliente. A guia delas não tem para onde sair.
      </p>

      <div className="card mb-4">
        <input className="input-field" placeholder="Buscar por empresa, CNPJ ou obrigação"
          value={busca} onChange={(e) => setBusca(e.target.value)} />
      </div>

      <div className="card">
        {erro && <p className="text-sm text-red-600">{erro}</p>}
        {!erro && !linhas && (
          <p className="flex items-center gap-2 text-sm text-gray-500">
            <Loader2 size={15} className="animate-spin" /> Carregando…
          </p>
        )}
        {linhas && (
          <>
            <p className="text-sm text-gray-500 mb-3">{lista.length} empresa(s)</p>
            {lista.length === 0 ? (
              <p className="text-gray-500 text-center py-8">Nenhuma empresa nesta situação.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="table-app">
                  <thead>
                    <tr className="text-left text-gray-500 border-b border-gray-200">
                      <th className="pr-3 font-medium">Empresa</th>
                      <th className="pr-3 font-medium">CNPJ</th>
                      <th className="pr-3 font-medium">O que falta</th>
                      <th className="pr-3 font-medium">Obrigações de envio</th>
                      <th className="pr-3 font-medium text-center">Tarefas abertas</th>
                    </tr>
                  </thead>
                  <tbody>
                    {lista.map((l) => (
                      <tr key={l.empresa_id} className="border-b border-gray-100">
                        <td className="pr-3 text-gray-800">
                          <Link to="/empresas" className="underline">{l.razao_social}</Link>
                        </td>
                        <td className="pr-3 text-gray-600 whitespace-nowrap">{l.cnpj || '-'}</td>
                        <td className="pr-3 text-gray-600">
                          {l.motivo}{l.email ? `: ${l.email}` : (l.telefone ? `: ${l.telefone}` : '')}
                        </td>
                        <td className="pr-3 text-gray-600">{l.obrigacoes.join(', ')}</td>
                        <td className="pr-3 text-gray-600 text-center">{l.tarefas_abertas}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
