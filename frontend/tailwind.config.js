module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  darkMode: 'class', // or 'media' based on preference
  theme: {
    extend: {
      colors: {
        'cloudflare-orange': '#f38020',
        'cloudflare-orange-dark': '#d66800',
        'cloudflare-secondary-gray': '#555555',
        'cloudflare-secondary-gray-light': '#6b6b6b',
        'cloudflare-secondary-gray-dark': '#404040',
        'cloudflare-dark-background': '#222222',
        'cloudflare-dark-background-alt': '#2a2a2a',
        'cloudflare-light-text': '#e0e0e0',
      },
    },
  },
  plugins: [],
}
