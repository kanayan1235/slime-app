
document.getElementById('upload-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById('image-input');
  const file = fileInput.files[0];
  if (!file) return;

  const progress = document.getElementById('progress-bar');
  progress.style.display = "block";
  progress.value = 10;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("https://slime-app-backend.onrender.com/upload", {
      method: "POST",
      body: formData,
    });
    progress.value = 80;
    const blob = await res.blob();
    const imgUrl = URL.createObjectURL(blob);
    document.getElementById('result-image').src = imgUrl;
    progress.value = 100;
  } catch (err) {
    alert("アップロードに失敗しました。");
    progress.style.display = "none";
  }
});
