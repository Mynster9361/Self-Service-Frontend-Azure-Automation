document.getElementById('btnSwitch').addEventListener('click', () => {
    const icon = document.querySelector('#btnSwitch i');
    if (document.documentElement.getAttribute('data-bs-theme') == 'dark') {
        document.documentElement.setAttribute('data-bs-theme', 'light');
        icon.classList.remove('bi-brightness-high-fill');
        icon.classList.add('bi-moon-stars-fill');
        icon.title = 'Switch to light mode';
        localStorage.setItem('theme', 'light');
    } else {
        document.documentElement.setAttribute('data-bs-theme', 'dark');
        icon.classList.remove('bi-moon-stars-fill');
        icon.classList.add('bi-brightness-high-fill');
        icon.title = 'Switch to dark mode';
        localStorage.setItem('theme', 'dark');
    }
});
