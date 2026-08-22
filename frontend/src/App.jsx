import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Empresas from './pages/Empresas';
import Setores from './pages/Setores';
import Usuarios from './pages/Usuarios';
import Tarefas from './pages/Tarefas';
import Obrigacoes from './pages/Obrigacoes';
import Substituicoes from './pages/Substituicoes';
import Notificacoes from './pages/Notificacoes';
import Grupos from './pages/Grupos';
import Relatorios from './pages/Relatorios';
import EValidador from './pages/EValidador';
import Documentos from './pages/Documentos';
import Modelos from './pages/Modelos';
import EnviarComprovante from './pages/EnviarComprovante';
import AtivarAcesso from './pages/AtivarAcesso';
import ImportarCronograma from './pages/ImportarCronograma';
import RelacaoObrigacoes from './pages/RelacaoObrigacoes';
import Layout from './components/Layout';

function PrivateRoute({ children }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="flex items-center justify-center h-screen">Carregando...</div>;
  }

  return user ? children : <Navigate to="/login" />;
}

function AppRoutes() {
  const { user } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" /> : <Login />} />
      <Route path="/enviar/:token" element={<EnviarComprovante />} />
      <Route path="/ativar/:token" element={<AtivarAcesso />} />
      <Route
        path="/"
        element={
          <PrivateRoute>
            <Layout />
          </PrivateRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="empresas" element={<Empresas />} />
        <Route path="setores" element={<Setores />} />
        <Route path="usuarios" element={<Usuarios />} />
        <Route path="tarefas" element={<Tarefas />} />
        <Route path="obrigacoes" element={<Obrigacoes />} />
        <Route path="substituicoes" element={<Substituicoes />} />
        <Route path="notificacoes" element={<Notificacoes />} />
        <Route path="grupos" element={<Grupos />} />
        <Route path="relatorios" element={<Relatorios />} />
        <Route path="evalidador" element={<EValidador />} />
        <Route path="documentos" element={<Documentos />} />
        <Route path="modelos" element={<Modelos />} />
        <Route path="importar-cronograma" element={<ImportarCronograma />} />
        <Route path="relatorios/obrigacoes" element={<RelacaoObrigacoes />} />
      </Route>
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <AppRoutes />
      </Router>
    </AuthProvider>
  );
}

export default App;