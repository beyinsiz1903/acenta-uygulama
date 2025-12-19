// MVP: Use package.json version as app version header
// (In real CI/CD, this can be replaced with build hash.)
import pkg from "../../package.json";

export const APP_VERSION = pkg?.version || "dev";
