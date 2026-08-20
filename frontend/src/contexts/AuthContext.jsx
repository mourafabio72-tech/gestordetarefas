import { createContext, useContext, useState, useEffect, useRef } from 'react';
import { authAPI } from '../services/api';
import { colherBilhete } from './bilhete';
import { decidirEntrada } from './entrada';

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
    const entrada = decidirEntrada({ bilhete, token });

    if (entrada.via === 'sso') {
      entrarPorBilhete(entrada.bilhete, entrada.tokenReserva);
      return;
    }

    if (entrada.via === 'sessao') {
      loadUser();
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

  const entrarPorBilhete = async (bilhete, tokenReserva) => {
    try {
      const response = await authAPI.sso(bilhete);
      localStorage.setItem('token', response.data.access_token);
      await loadUser();
      // O `loadUser` engole a própria falha e apaga o token. Sem esta conferência,
      // um bilhete aceito cujo /me falhasse depois jogaria a pessoa na tela de
      // login sem uma palavra de explicação.
      if (!localStorage.getItem('token')) setAviso(AVISO_SSO);
    } catch (error) {
      // Bilhete recusado (vencido, já usado, 429 do limite por IP) não pode
      // custar a sessão de quem já estava dentro: devolve o token anterior e
      // segue com ele. Só quando ele também não vale é que a pessoa vê a tela
      // de senha -- e aí o aviso é o mesmo para todos os motivos, porque
      // distinguir entregaria a quem tenta adivinhar quais contas existem.
      if (tokenReserva) {
        localStorage.setItem('token', tokenReserva);
        await loadUser();
        if (!localStorage.getItem('token')) setAviso(AVISO_SSO);
        return;
      }
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
