export const useLoggedInState = function () {
  const auth = useMealieAuth();
  const route = useRoute();

  const loggedIn = computed(() => auth.loggedIn.value);
  const routeGroupSlug = computed(() => normalizeRouteParam(route.params.groupSlug));
  const userGroupSlug = computed(() => normalizeRouteParam(auth.user.value?.groupSlug));
  const isOwnGroup = computed(() => {
    if (!routeGroupSlug.value) {
      return loggedIn.value;
    }
    else {
      return loggedIn.value && userGroupSlug.value === routeGroupSlug.value;
    }
  });

  return { loggedIn, isOwnGroup };
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
