import { render } from "@coldtea/pr-lens-renderer";
import { safeParseGraphDoc } from "@coldtea/pr-lens-schema";
import { config } from "zod";
config({ jitless: true });
globalThis.PrLens = { render, safeParseGraphDoc };
