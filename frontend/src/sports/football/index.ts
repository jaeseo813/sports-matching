import { Goal } from "lucide-react";
import type { Sport } from "../types";
import Page from "./Page";

export const football: Sport = {
  id: "football",
  name: "축구/풋살",
  tagline: "풋살 5:5 / 6:6",
  icon: Goal,
  bg: "bg-lime",
  fg: "text-night",
  Page,
};
