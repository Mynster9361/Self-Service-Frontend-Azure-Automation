// Immediately set the theme from localStorage when the script runs
const theme = localStorage.getItem('theme');
if (theme) {
    document.documentElement.setAttribute('data-bs-theme', theme);
}