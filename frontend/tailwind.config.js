module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: 'class', // or 'media' based on preference
  theme: {
    extend: {
      colors: {
        'cloudflare-orange': '#f38020',
        'cloudflare-secondary-gray': '#555555',
        'cloudflare-dark-background': '#222222',
        'cloudflare-light-text': '#e0e0e0',
      },
    },
  },
  plugins: [],
}
