import { Empty, Icon, Layout } from './components';
import { UserPage } from './UserPage';
import { AdminPage } from './AdminPage';

export function App() {
  const path = window.location.pathname.replace(/\/$/, '') || '/';
  if (path === '/usuario') return <UserPage />;
  if (path === '/admin') return <AdminPage />;
  if (path !== '/')
    return (
      <Layout>
        <div className="page-shell">
          <Empty title="Página não encontrada" icon="info">
            Escolha uma das visões para continuar.
          </Empty>
          <a href="/" className="button button-primary">
            Voltar ao início
          </a>
        </div>
      </Layout>
    );
  return (
    <Layout>
      <div className="page-shell home-shell">
        <section className="home-intro">
          <div>
            <p className="eyebrow">MENOS ESPERA. MAIS ORGANIZAÇÃO.</p>
            <h1>
              Cada atendimento
              <br />
              começa com <em>uma vez.</em>
            </h1>
            <p>
              Um jeito simples de organizar a fila e acompanhar o atendimento. Escolha como você
              quer começar.
            </p>
            <div className="home-pills">
              <span>
                <Icon name="check" size={16} />
                Senha digital
              </span>
              <span>
                <Icon name="refresh" size={16} />
                Atualização automática
              </span>
            </div>
          </div>
          <div className="home-art" aria-hidden="true">
            <div className="art-back" />
            <div className="art-ticket">
              <span className="brand-mark">
                <Icon name="ticket" size={30} />
              </span>
              <span className="eyebrow">EM FILA</span>
              <strong>
                Sua próxima vez,
                <br />
                mais tranquila.
              </strong>
              <div className="art-divider" />
              <span>
                <span className="sync-dot" />
                Um passo de cada vez.
              </span>
            </div>
            <span className="art-stamp">
              <Icon name="check" />
              Pronto para atender
            </span>
          </div>
        </section>
        <div className="home-views">
          <a className="home-view" href="/usuario">
            <span className="home-view-icon">
              <Icon name="ticket" size={27} />
            </span>
            <div>
              <p className="eyebrow">PARA QUEM VAI SER ATENDIDO</p>
              <h2>Acessar como usuário</h2>
              <p>Retire uma senha e acompanhe sua vez em tempo real.</p>
            </div>
            <span className="round-arrow">
              <Icon name="arrow" />
            </span>
          </a>
          <a className="home-view admin-view" href="/admin">
            <span className="home-view-icon">
              <Icon name="grid" size={26} />
            </span>
            <div>
              <p className="eyebrow">PARA QUEM ORGANIZA O ATENDIMENTO</p>
              <h2>Acessar como administrador</h2>
              <p>Gerencie filas, chame senhas e conduza cada atendimento.</p>
            </div>
            <span className="round-arrow">
              <Icon name="arrow" />
            </span>
          </a>
        </div>
        <p className="home-disclaimer">
          <Icon name="info" size={16} />
          Demonstração acadêmica local. A escolha da visão não realiza login nem restringe o acesso.
        </p>
      </div>
    </Layout>
  );
}
