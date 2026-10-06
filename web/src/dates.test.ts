import { describe, expect, it } from "vitest";
import { localIso } from "./dates";

describe("localIso", () => {
  it("TC-0182: uses the local calendar day, not the UTC day", () => {
    // 23:30 local on 1 December is still 1 December here, whatever UTC says.
    expect(localIso(new Date(2026, 11, 1, 23, 30))).toBe("2026-12-01");
    // 00:05 local on 1 January is already 1 January here.
    expect(localIso(new Date(2026, 0, 1, 0, 5))).toBe("2026-01-01");
  });

  it("pads single-digit months and days", () => {
    expect(localIso(new Date(2027, 2, 4, 12, 0))).toBe("2027-03-04");
  });
});
