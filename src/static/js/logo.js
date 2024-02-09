window.onload = function() {
    // Check if the image data is in localStorage
    let imageData = localStorage.getItem('bannerImage');

    if (imageData) {
        // If the image data is in localStorage, use it
        document.querySelector('#bannerImage').src = imageData;
    } else {
        // If the image data is not in localStorage, fetch it
        fetch('/static/images/banner-192.webp')
            .then(response => response.blob())
            .then(blob => {
                // Convert the blob to a data URL and store it in localStorage
                let reader = new FileReader();
                reader.onloadend = function() {
                    localStorage.setItem('bannerImage', reader.result);
                    // Set the src attribute of the img tag to the data URL
                    document.querySelector('#bannerImage').src = reader.result;
                }
                reader.readAsDataURL(blob);
            });
    }
}