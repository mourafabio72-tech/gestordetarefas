import { createContext, useContext, useState, useEffect, useRef } from 'react';
import { authAPI } from '../services/api';
import { colherBilhete } from './bilhete';

const AuthContext = createContext(null);

// Aviso único de recusa da entrada pelo Hub. O motivo real (bilhete vencido, já
// usado, conta sem cadastro, bloqueada ou inativa) fica só no log do servidor:
// dizer aqui qual dos casos aconteceu entregaria a quem tenta adivinhar um jeito
// de descobrir quais contas existem.
const AVISO_SSO = 'Não foi possível entrar pelo portal Zoaria. ' +
  'Entre com seu e-mail e senha, ou procure quem administra o sistema.';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [aviso, setAviso] = useState('');
  const iniciado = useRef(false);

  useEffect(() => {
    // O StrictMode do React monta duas vezes em desenvolvimento, e bilhete é de
    // uso único: sem esta trava, a segunda montagem gastaria o mesmo bilhete e a
    // pessoa veria o aviso de recusa depois de ter entrado.
    if (iniciado.current) return;
    iniciado.current = true;

    const bilhete = colherBilhete(window.location, window.history);
    const token = localStorage.getItem('token');

    if (token) {
      // Quem já tem sessão aberta não é derrubado por um bilhete que chega. O
      // bilhete sai da URL do mesmo jeito, porque ele não pode ficar na barra.
      loadUser();
      return;
    }

    if (bilhete) {
      entrarPorBilhete(bilhete);
      return;
    }

    setLoading(false);
  }, []);

  const loadUser = async () => {
    try {
      const response = await authAPI.me();
      setUser(response.data);
    } catch (error) {
      localStorage.removeItem('token');
    } finally {
      setLoading(false);
    }
  };

  const entrarPorBilhete = async (bilhete) => {
    try {
      const response = await authAPI.sso(bilhete);
      localStorage.setItem('token', response.data.access_token);
      await loadUser();
      // O `loadUser` engole a própria falha e apaga o token. Sem esta conferência,
      // um bilhete aceito cujo /me falhasse depois jogaria a pessoa na tela de
      // login sem uma palavra de explicação.
      if (!localStorage.getItem('token')) setAviso(AVISO_SSO);
    } catch (error) {
      // Qualquer falha cai na tela de login com o mesmo aviso, inclusive o 429
      // do limite por IP: quem está do lado de fora não precisa saber a diferença.
      setAviso(AVISO_SSO);
      setLoading(false);
    }
  };

  const login = async (email, senha) => {
    const response = await authAPI.login({ email, senha });
    localStorage.setItem('token', response.data.access_token);
    await loadUser();
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  const limparAviso = () => setAviso('');

  return (
    <AuthContext.Provider value={{ user, login, logout, loading, aviso, limparAviso }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
