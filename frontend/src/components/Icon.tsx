import type { ReactNode, SVGProps } from "react"

export type IconName =
  | "home"
  | "messages"
  | "rooms"
  | "knowledge"
  | "chevron"
  | "eye"
  | "eye-off"
  | "arrow"
  | "shield"
  | "menu"
  | "close"
  | "logout"
  | "spark"
  | "check"
  | "lock"
  | "dots"
  | "plus"
  | "user"
  | "settings"
  | "search"
  | "paperclip"
  | "key"
  | "upload"
  | "link"
  | "file"
  | "trash"

const paths: Record<IconName, ReactNode> = {
  home: <><path d="m3.5 10 8.5-7 8.5 7" /><path d="M5.5 9v10h13V9M9 19v-6h6v6" /></>,
  messages: <><path d="M20 11.5a7.5 7.5 0 0 1-8 7.5 8.6 8.6 0 0 1-3.7-.8L4 20l1.4-3.7A7.1 7.1 0 0 1 4 12.5 7.5 7.5 0 0 1 12 5a7.5 7.5 0 0 1 8 6.5Z" /><path d="M8 11h8M8 14h5" /></>,
  rooms: <><rect x="4" y="4" width="16" height="16" rx="3" /><path d="M8 8h8M8 12h5M8 16h7" /></>,
  knowledge: <><path d="M5 4.5A2.5 2.5 0 0 1 7.5 2H19v17H7.5A2.5 2.5 0 0 0 5 21.5v-17Z" /><path d="M5 17a2.5 2.5 0 0 1 2.5-2.5H19M9 6h6M9 9h6" /></>,
  chevron: <path d="m8 10 4 4 4-4" />,
  eye: <><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z" /><circle cx="12" cy="12" r="2.5" /></>,
  "eye-off": <><path d="m3 3 18 18M10.6 6.2A10 10 0 0 1 12 6c6.5 0 10 6 10 6a15 15 0 0 1-3 3.7M6.2 6.5C3.5 8.2 2 12 2 12s3.5 6 10 6c1.2 0 2.3-.2 3.3-.6" /><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" /></>,
  arrow: <><path d="M4 12h15M13 6l6 6-6 6" /></>,
  shield: <><path d="M12 3 19 6v5c0 4.6-3 8.2-7 10-4-1.8-7-5.4-7-10V6l7-3Z" /><path d="m9 12 2 2 4-4" /></>,
  menu: <><path d="M4 7h16M4 12h16M4 17h16" /></>,
  close: <><path d="m6 6 12 12M18 6 6 18" /></>,
  logout: <><path d="M10 4H5v16h5M14 8l4 4-4 4M8 12h10" /></>,
  spark: <><path d="m12 3 1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3Z" /><path d="m19 15 .8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15Z" /></>,
  check: <path d="m5 12 4.5 4.5L19 7" />,
  lock: <><rect x="4" y="10" width="16" height="11" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3" /></>,
  dots: <><circle cx="5" cy="12" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="19" cy="12" r="1" /></>,
  plus: <><path d="M12 5v14M5 12h14" /></>,
  user: <><circle cx="12" cy="8" r="3.5" /><path d="M5 20c.6-3.3 3.1-5 7-5s6.4 1.7 7 5" /></>,
  settings: <><circle cx="12" cy="12" r="3" /><path d="m19.4 15 .1.1 1.2.9-1.5 2.6-1.4-.6a7.8 7.8 0 0 1-1.6.9L16 20.5h-3l-.3-1.6a7.8 7.8 0 0 1-1.6-.9l-1.4.6-1.5-2.6 1.2-.9a6.6 6.6 0 0 1 0-1.8l-1.2-.9 1.5-2.6 1.4.6a7.8 7.8 0 0 1 1.6-.9l.3-1.6h3l.3 1.6a7.8 7.8 0 0 1 1.6.9l1.4-.6 1.5 2.6-1.2.9a6.6 6.6 0 0 1-.2 1.7Z" /></>,
  search: <><circle cx="10.8" cy="10.8" r="6.3" /><path d="m15.5 15.5 4.2 4.2" /></>,
  paperclip: <path d="m8 12.5 6.8-6.8a3.2 3.2 0 0 1 4.5 4.5l-8.9 8.9a5 5 0 0 1-7.1-7.1l8.5-8.5" />,
  key: <><circle cx="8" cy="15.5" r="4.5" /><path d="m11.2 12.3 8.3-8.3 2 2-2 2 1.8 1.8-2.1 2.1-1.8-1.8-3 3" /></>,
  upload: <><path d="M12 16V4m-4 4 4-4 4 4" /><path d="M5 14v5h14v-5" /></>,
  link: <><path d="M10 13a5 5 0 0 0 7.1 0l2-2A5 5 0 0 0 12 3.9l-1.1 1.1" /><path d="M14 11a5 5 0 0 0-7.1 0l-2 2A5 5 0 0 0 12 20.1l1.1-1.1" /></>,
  file: <><path d="M6 3h8l4 4v14H6z" /><path d="M14 3v5h5M9 13h6M9 17h6" /></>,
  trash: <><path d="M4 7h16M10 11v6M14 11v6M6 7l1 14h10l1-14M9 7V4h6v3" /></>,
}

interface IconProps extends SVGProps<SVGSVGElement> {
  name: IconName
}

export function Icon({ name, ...props }: IconProps) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      {paths[name]}
    </svg>
  )
}
