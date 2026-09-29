import { describe, expect, it } from "vitest";
import { profileNameUpdate } from "@/lib/profileName";
import { readProfileSaveError } from "@/lib/api/profile";
import axios from "axios";

describe("profile name update", () => {
  it("trims a real name and sends only first and last name", () => {
    expect(profileNameUpdate("  Nia  ", "  Kamau  ")).toEqual({
      ok: true,
      first_name: "Nia",
      last_name: "Kamau",
    });
  });

  it("rejects an empty or whitespace name", () => {
    expect(profileNameUpdate(" ", "Kamau")).toEqual({
      ok: false,
      message: "First name is required.",
    });
    expect(profileNameUpdate("Nia", "   ")).toEqual({
      ok: false,
      message: "Last name is required.",
    });
    expect(profileNameUpdate("", "")).toEqual({
      ok: false,
      message: "Enter your first and last name.",
    });
  });

  it("keeps legitimate punctuation in a name", () => {
    expect(profileNameUpdate("Mary-Jane", "O'Brien")).toEqual({
      ok: true,
      first_name: "Mary-Jane",
      last_name: "O'Brien",
    });
  });

  it("reads a profile save failure without exposing a token", () => {
    const error = new axios.AxiosError("bad");
    error.response = {
      status: 400,
      data: { first_name: ["This field may not be blank."] },
      statusText: "Bad Request",
      headers: {},
      config: { headers: {} } as never,
    };
    expect(readProfileSaveError(error)).toBe("This field may not be blank.");
  });
});
