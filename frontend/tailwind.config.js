/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        amazon: {
          orange: '#FF9900',
          dark: '#131921',
          blue: '#146EB4',
          lightblue: '#37A6E0',
        },
      },
    },
  },
  plugins: [],
}
