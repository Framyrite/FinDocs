import brandMark from "../assets/logo.png";

export type Tab = "chat" | "documents";

interface NavbarProps {
  activeTab: Tab;
  onTabChange: (tab: Tab) => void;
}

const tabs: { id: Tab; label: string }[] = [
  { id: "chat", label: "Чат" },
  { id: "documents", label: "Мои документы" },
];

export function Navbar({ activeTab, onTabChange }: NavbarProps) {
  return (
    <header className="app-header">
      <button
        type="button"
        className="brand"
        onClick={() => onTabChange("chat")}
        aria-label="FinDocs — перейти в чат"
      >
        <img className="brand-symbol" src={brandMark} alt="" />

        <span className="brand-copy">
          <span className="brand-wordmark">
            <span className="brand-fin">Fin</span>
            <span className="brand-docs">Docs</span>
          </span>

          <span className="brand-tagline">
            FinDocs · Учитесь с опорой на факты
          </span>
        </span>
      </button>

      <nav className="main-nav" aria-label="Основная навигация">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`nav-tab ${
              activeTab === tab.id ? "nav-tab--active" : ""
            }`}
            aria-current={activeTab === tab.id ? "page" : undefined}
            onClick={() => onTabChange(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>
    </header>
  );
}
