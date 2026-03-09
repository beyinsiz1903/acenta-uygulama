export function normalizeRoleName(role) {
  if (!role) {
    return "";
  }

  const normalized = String(role).trim().toLowerCase().replace(/[-\s]+/g, "_");
  if (["admin", "superadmin", "super_admin"].includes(normalized)) {
    return "super_admin";
  }
  return normalized;
}

export function normalizeRoles(userOrRoles) {
  const rawRoles = Array.isArray(userOrRoles)
    ? userOrRoles
    : [
        ...((userOrRoles && Array.isArray(userOrRoles.roles)) ? userOrRoles.roles : []),
        userOrRoles?.role,
      ];

  return rawRoles
    .map((role) => normalizeRoleName(role))
    .filter((role, index, list) => role && list.indexOf(role) === index);
}

export function hasAnyRole(userOrRoles, allowedRoles = []) {
  const userRoles = normalizeRoles(userOrRoles);
  const allowed = normalizeRoles(allowedRoles);
  return allowed.some((role) => userRoles.includes(role));
}