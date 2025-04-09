import './assets/main.css'

import { createApp } from 'vue'
import App from './App.vue'
import PrimeVue from 'primevue/config'
import Aura from '@primeuix/themes/aura'
import { definePreset } from '@primeuix/themes'

const CustomPreset = definePreset(Aura, {
  semantic: {
    primary: {
      50: '{teal.50}',
      100: '{teal.100}',
      200: '{teal.200}',
      300: '{teal.300}',
      400: '{teal.400}',
      500: '{teal.500}',
      600: '{teal.600}',
      700: '{teal.700}',
      800: '{teal.800}',
      900: '{teal.900}',
      950: '{teal.950}',
    },
  },
  components: {
    card: {
      root: {
        background: '{teal.50}',
        color: '{surface.700}',
      },
      subtitle: {
        color: '{surface.500}',
      },
    },
    fileupload: {
      header: {
        background: '{sky.50}',
        color: '{amber.700}',
      },
    },
    button: {
      root: {
        primary: { background: '{amber.700}', color: '{white}' },
      },
    },
  },
})

const app = createApp(App)
app.use(PrimeVue, {
  theme: {
    preset: CustomPreset,
    options: { darkModeSelector: false },
  },
})
app.mount('#app')
