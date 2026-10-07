import type { ComponentType } from "react";
import type { LucideIcon } from "lucide-react";

export interface Sport {
  id: string; // URL: /sports/:id
  name: string;
  tagline: string;
  icon: LucideIcon;
  bg: string; // Tailwind 배경색 클래스
  fg: string; // bg 위에서 읽히는 글자색 클래스
  Page: ComponentType; // 종목 전용 화면 (종목 담당자가 이 폴더 안에서 작업)
}
