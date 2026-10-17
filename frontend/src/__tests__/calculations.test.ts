import { describe, expect, it } from "vitest";
import { seedBenchmark, seedTransactions } from "../data/seeds";
import {
  agentRemainingPct,
  agentUtilizationPct,
  filterTransactions,
  fusionWeightSum,
  latencyTotalMs,
  obfuscationDeltaPp,
  scoreRiskBand,
} from "../domain/calculations";

describe("calculated fields → BR", () => {
  it("agent utilization / remaining (BR-AG-1)", () => {
    expect(agentUtilizationPct(38400, 50000)).toBe(77);
    expect(agentRemainingPct(38400, 50000)).toBe(23);
    expect(agentUtilizationPct(0, 0)).toBe(0);
  });

  it("score bands at boundaries (BR-MON-2)", () => {
    expect(scoreRiskBand(0)).toBe("safe");
    expect(scoreRiskBand(0.4)).toBe("safe");
    expect(scoreRiskBand(0.41)).toBe("warning");
    expect(scoreRiskBand(0.75)).toBe("warning");
    expect(scoreRiskBand(0.76)).toBe("danger");
    expect(scoreRiskBand(1)).toBe("danger");
  });

  it("fusion sum (BR-SET-1)", () => {
    expect(fusionWeightSum(25, 32, 43)).toBe(100);
  });

  it("latency total matches stages (BR-AN-1)", () => {
    expect(latencyTotalMs(seedBenchmark.latencyStages)).toBe(309);
    expect(latencyTotalMs(seedBenchmark.latencyStages)).toBe(seedBenchmark.totalMedianMs);
  });

  it("obfuscation delta (BR-AN-1)", () => {
    expect(obfuscationDeltaPp(92, 40)).toBe(52);
  });

  it("empty filter result (BR-MON-3)", () => {
    const shown = filterTransactions(seedTransactions, "zzzz-no-match", "All risk levels");
    expect(shown).toEqual([]);
  });

  it("action filter BLOCK only", () => {
    const shown = filterTransactions(seedTransactions, "", "BLOCK");
    expect(shown.every((t) => t.action === "BLOCK")).toBe(true);
  });
});
