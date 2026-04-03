import { describe, expect, test } from "bun:test";

import { renderStatus } from "./status";

describe("renderStatus", () => {
  test("renders connected status copy", () => {
    expect(renderStatus("connected")).toBe("Connected");
  });

  test("renders disconnected status copy", () => {
    expect(renderStatus("disconnected")).toBe("Disconnected");
  });
});
