/**
 * A destination in the primary navigation.
 *
 * `icon` is a *name*, not a component. Navigation lists are declared in server
 * components and consumed by client components, and only serialisable data can
 * cross that boundary — so the icon is resolved from a registry on the client
 * side (see mobile-navigation.tsx). This also keeps navigation as plain data,
 * which is what it will be when it is driven by user state in Phase 3.
 */
export type NavIconName = "home" | "recommend" | "policies" | "profile" | "help";

export type NavItem = {
  href: string;
  label: string;
  /** Required for mobile navigation, where labels are very small. */
  icon?: NavIconName;
};
