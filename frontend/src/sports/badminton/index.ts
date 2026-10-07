import { Feather } from "lucide-react";
import type { Sport } from "../types";
import Page from "./Page";

export const badminton: Sport = {
  id: "badminton",
  name: "배드민턴",
  tagline: "복식 / 단식",
  icon: Feather,
  bg: "bg-lime",
  fg: "text-night",
  Page,
};
