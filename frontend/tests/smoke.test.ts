import { describe, expect, it } from "vitest";

describe("smoke", () => {
  it("keeps the test runner wired", () => {
    expect("Requirements Impact Radar").toContain("Radar");
  });
});
