<script setup>
/**
 * Login — bewusst vollständig nackt: kein App-Name, kein Branding, keine
 * Kopf-/Fußzeile, keine Info darüber, was hier läuft. Nur ein zentriertes
 * Formular auf leerem Grund. Der Browser-Tab bekommt einen neutralen Titel.
 */
useHead({ title: 'Anmelden' })

const { login } = useAuth()

const username = ref('')
const password = ref('')
const pending = ref(false)
const error = ref('')

const submit = async () => {
  if (pending.value) return
  if (!username.value || !password.value) {
    error.value = 'Benutzername und Passwort eingeben.'
    return
  }
  pending.value = true
  error.value = ''
  try {
    await login(username.value, password.value)
    // Erfolg → App-Zustand ist 'authed', app.vue rendert die eigentliche Oberfläche.
  } catch (e) {
    // Bewusst generisch (Backend liefert dieselbe Meldung bei unbekanntem
    // Benutzer und falschem Passwort) — keine Hinweise, was genau falsch war.
    error.value = e?.data?.detail || 'Anmeldung fehlgeschlagen.'
    password.value = ''
  } finally {
    pending.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center px-4">
    <div class="w-full max-w-sm">
      <form
        class="space-y-4 rounded-2xl border border-neutral-200 bg-white p-8 shadow-sm dark:border-neutral-800 dark:bg-neutral-900"
        @submit.prevent="submit"
      >
        <div class="space-y-3">
          <UInput
            v-model="username"
            name="username"
            type="text"
            autocomplete="username"
            placeholder="Benutzername"
            size="lg"
            :disabled="pending"
            autofocus
          />
          <UInput
            v-model="password"
            name="password"
            type="password"
            autocomplete="current-password"
            placeholder="Passwort"
            size="lg"
            :disabled="pending"
          />
        </div>

        <p
          v-if="error"
          role="alert"
          class="text-sm text-red-600 dark:text-red-400"
        >
          {{ error }}
        </p>

        <UButton
          type="submit"
          block
          size="lg"
          :loading="pending"
          class="w-full justify-center"
        >
          Anmelden
        </UButton>
      </form>
    </div>
  </div>
</template>
