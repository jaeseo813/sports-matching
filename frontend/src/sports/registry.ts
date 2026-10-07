import { badminton } from "./badminton";
import { basketball } from "./basketball";
import { football } from "./football";
import type { Sport } from "./types";

// 종목을 추가하려면 src/sports/<id>/ 폴더를 만들고 여기에 등록한다.
export const sports: Sport[] = [basketball, football, badminton];
