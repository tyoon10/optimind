// See https://svelte.dev/docs/kit/types#app
declare global {
  namespace App {
    interface Platform {
      env?: {
        GITHUB_CLIENT_SECRET?: string;
      };
    }
  }
}

export {};
