import { useState } from 'react';
import { empresasAPI } from '../services/api';
import { mensagemDeErro } from '../services/erroApi';
import { Users, Download } from 'lucide-react';

// Excel das empresas ativas, com a forma de tributação e a equipe de cada setor.
export default function RelatorioEquipe() {
  const [baixando, setBaixando] = useState(false);
  const [erro, setErro] = useState('');

  const baixar = async () => {
    setBaixando(true); setErro('');
    try {
      await empresasAPI.baixarRelatorioEquipe();
    } catch (e) {
      setErro(mensagemDeErro(e, 'Não foi possível gerar o relatório.'));
    } finally { setBaixando(false); }
  };

  return (
    <div>
      <div className="flex items-center gap-2 mb-6">
        <Users className="text-primary-700" />
        <h1 className="text-2xl font-bold text-gray-800">Empresas e equipe</h1>
      </div>
      <div className="card">
        <p className="text-sm text-gray-600 mb-4">
          Excel com uma linha por empresa ativa: forma de tributação, segmento, grupo e, em cada setor, os
          colaboradores vinculados, com o principal primeiro. "sem responsável" é setor atendido sem ninguém
          vinculado. Coluna vazia é setor sem vínculo com a empresa.
        </p>
        <button onClick={baixar} disabled={baixando} className="btn-primary flex items-center gap-2 disabled:opacity-40">
          <Download size={18} /> {baixando ? 'Gerando…' : 'Baixar Excel'}
        </button>
        {erro && <p className="text-sm text-red-600 mt-3">{erro}</p>}
      </div>
    </div>
  );
}
