export const useLoggedInState = function () {
  const auth = useMealieAuth();
  const route = useRoute();

  const loggedIn = computed(() => auth.loggedIn.value);
  const routeGroupSlug = computed(() => normalizeRouteParam(route.params.groupSlug));
  const userGroupSlug = computed(() => normalizeRouteParam(auth.user.value?.groupSlug));
  const isHomeRoute = computed(() => routeGroupSlug.value === "home");
  const groupSlug = computed(() => {
    if (isHomeRoute.value && userGroupSlug.value) {
      return userGroupSlug.value;
    }

    return routeGroupSlug.value || userGroupSlug.value;
  });
  const isOwnGroup = computed(() => {
    if (!loggedIn.value) {
      return false;
    }

    if (!routeGroupSlug.value || isHomeRoute.value) {
      return true;
    }

    return userGroupSlug.value === routeGroupSlug.value;
  });

  return { loggedIn, isOwnGroup, groupSlug, isHomeRoute };
};

function normalizeRouteParam(value: unknown) {
  const firstValue = Array.isArray(value) ? value[0] : value;
  if (!firstValue) {
    return "";
  }

  const rawValue = String(firstValue).trim();
  try {
    return decodeURIComponent(rawValue).trim().toLocaleLowerCase();
  }
  catch {
    return rawValue.toLocaleLowerCase();
  }
}
