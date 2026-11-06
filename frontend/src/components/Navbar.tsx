// frontend/src/components/Navbar.tsx
import React from "react";

export type Tab = "chat" | "documents";

interface NavbarProps {
  activeTab: Tab;
  onTabChange: (tab: Tab) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ activeTab, onTabChange }) => {
  const tabs: { id: Tab; label: string }[] = [
    { id: "chat", label: "Чат" },
    { id: "documents", label: "Мои документы" },
  ];

  return (
    <nav
      style={{
        display: "flex",
        gap: "8px",
        marginBottom: "24px",
        borderBottom: "1px solid #ddd",
        paddingBottom: "12px",
      }}
    >
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onTabChange(tab.id)}
          style={{
            padding: "8px 16px",
            backgroundColor: activeTab === tab.id ? "#0b5c6b" : "transparent",
            color: activeTab === tab.id ? "white" : "#333",
            border: "1px solid #0b5c6b",
            borderRadius: "6px",
            cursor: "pointer",
            fontWeight: activeTab === tab.id ? "bold" : "normal",
            transition: "all 0.2s",
          }}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
};
