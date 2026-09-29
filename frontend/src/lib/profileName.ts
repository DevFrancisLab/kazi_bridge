export function profileNameUpdate(firstName: string, lastName: string):
  | { ok: true; first_name: string; last_name: string }
  | { ok: false; message: string } {
  const first_name = firstName.trim();
  const last_name = lastName.trim();
  if (!first_name && !last_name) {
    return { ok: false, message: "Enter your first and last name." };
  }
  if (!first_name) {
    return { ok: false, message: "First name is required." };
  }
  if (!last_name) {
    return { ok: false, message: "Last name is required." };
  }
  return { ok: true, first_name, last_name };
}
