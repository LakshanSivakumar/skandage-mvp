/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./core/templates/**/*.html",
        "./core/views.py",
    ],
    theme: {
        extend: {},
    },
    plugins: [
        require('@tailwindcss/typography'),
    ],
}
