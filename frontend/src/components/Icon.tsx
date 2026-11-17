import type { CSSProperties } from "react";

import messageDots from "../assets/icons/message-dots.svg";
import files from "../assets/icons/files.svg";
import plus from "../assets/icons/plus.svg";
import upload from "../assets/icons/upload.svg";
import paperclip from "../assets/icons/paperclip.svg";
import send from "../assets/icons/send.svg";
import search from "../assets/icons/search.svg";
import chevronDown from "../assets/icons/chevron-down.svg";
import dotsVertical from "../assets/icons/dots-vertical.svg";
import trash from "../assets/icons/trash.svg";
import x from "../assets/icons/x.svg";
import check from "../assets/icons/check.svg";
import loader from "../assets/icons/loader-2.svg";
import alertTriangle from "../assets/icons/alert-triangle.svg";
import fileDescription from "../assets/icons/file-description.svg";

// Vite импортирует SVG как URL отдельных файлов. Контуры не дублируются в JSX.
// Реестр ограничивает name доступными иконками и проверяется TypeScript.
const iconSources = {
  "message-dots": messageDots,
  files,
  plus,
  upload,
  paperclip,
  send,
  search,
  "chevron-down": chevronDown,
  "dots-vertical": dotsVertical,
  trash,
  x,
  check,
  "loader-2": loader,
  "alert-triangle": alertTriangle,
  "file-description": fileDescription,
};

interface IconProps {
  name: keyof typeof iconSources;
  size?: number;
  className?: string;
}

export function Icon({ name, size = 20, className = "" }: IconProps) {
  // CSS-маска берёт из SVG форму, а цвет получает через currentColor.
  // Дополнительный тип разрешает пользовательскую CSS-переменную --icon-url.
  const style: CSSProperties & { "--icon-url": string } = {
    "--icon-url": `url("${iconSources[name]}")`,
    width: size,
    height: size,
  };

  // Иконка декоративная: доступное название задаёт текст или aria-label кнопки.
  return (
    <span
      className={`app-icon ${className}`}
      style={style}
      aria-hidden="true"
    />
  );
}
