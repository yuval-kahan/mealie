export default defineNuxtPlugin({
  async setup() {
    const auth = useAuthBackend();

    console.debug("Initializing auth plugin");
    await auth.getSession();
    if (auth.status.value === "authenticated") {
      try {
        await auth.refresh();
      }
      catch (error) {
        console.warn("Unable to renew the current session", error);
      }
    }
    console.debug("Auth plugin initialized");
  },
});
