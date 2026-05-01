import { beforeEach, describe, expect, it, vi } from "vitest";

import { api, clearToken, getToken } from "./api";

describe("api auth", () => {
  beforeEach(() => {
    clearToken();
  });

  it("stores JWT after login", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ access_token: "abc123" }),
      }),
    );

    await api.login({ email: "agent@loanvati.test", password: "password" });
    expect(getToken()).toBe("abc123");
  });
});
