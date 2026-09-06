/**
 * CropPulse – Upload Page JS
 * Handles drag-and-drop image upload, preview, form submission,
 * and progress display for disease detection.
 */

document.addEventListener("DOMContentLoaded", () => {
  Auth.requireAuth();

  const dropZone    = document.getElementById("upload-drop-zone");
  const fileInput   = document.getElementById("leaf-file-input");
  const previewEl   = document.getElementById("image-preview");
  const previewWrap = document.getElementById("preview-wrapper");
  const uploadBtn   = document.getElementById("upload-btn");
  const uploadForm  = document.getElementById("upload-form");
  const progressBar = document.getElementById("upload-progress");
  const farmSelect  = document.getElementById("farm-select");

  let selectedFile = null;

  // ── Load user's farms ───────────────────────────────────────────────────
  async function loadFarms() {
    try {
      const res = await CropPulseAPI.auth.getMyFarms();
      const farms = res.farms || [];
      farmSelect.innerHTML = '<option value="">No specific farm</option>';
      farms.forEach(f => {
        const opt = document.createElement("option");
        opt.value = f.farm_id;
        opt.textContent = f.name;
        farmSelect.appendChild(opt);
      });
    } catch (e) {
      console.warn("Could not load farms:", e);
    }
  }
  loadFarms();

  // ── Drag & Drop Events ──────────────────────────────────────────────────
  ["dragenter", "dragover", "dragleave", "drop"].forEach(event => {
    dropZone.addEventListener(event, e => { e.preventDefault(); e.stopPropagation(); });
  });

  ["dragenter", "dragover"].forEach(event => {
    dropZone.addEventListener(event, () => dropZone.classList.add("drag-over"));
  });

  ["dragleave", "drop"].forEach(event => {
    dropZone.addEventListener(event, () => dropZone.classList.remove("drag-over"));
  });

  dropZone.addEventListener("drop", e => {
    const files = e.dataTransfer?.files;
    if (files?.length) handleFile(files[0]);
  });

  dropZone.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", () => {
    if (fileInput.files?.length) handleFile(fileInput.files[0]);
  });

  // ── Handle Selected File ────────────────────────────────────────────────
  function handleFile(file) {
    const allowed = ["image/jpeg", "image/jpg", "image/png", "image/webp", "image/bmp"];
    if (!allowed.includes(file.type)) {
      Utils.showToast("Only JPG, PNG, WEBP, or BMP images are allowed.", "error");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      Utils.showToast("File too large. Maximum size is 10MB.", "error");
      return;
    }

    selectedFile = file;
    const reader = new FileReader();
    reader.onload = e => {
      previewEl.src = e.target.result;
      sessionStorage.setItem("ag_last_uploaded_preview", e.target.result);
      previewWrap.classList.remove("hidden");
      previewEl.classList.add("img-preview-enter");
      uploadBtn.disabled = false;

      // Show file info
      const infoEl = document.getElementById("file-info");
      if (infoEl) {
        infoEl.textContent = `${file.name} — ${Utils.formatBytes(file.size)}`;
        infoEl.classList.remove("hidden");
      }
    };
    reader.readAsDataURL(file);
  }

  // ── Form Submit ─────────────────────────────────────────────────────────
  uploadForm?.addEventListener("submit", async (e) => {
    e.preventDefault();

    if (!selectedFile) {
      Utils.showToast("Please select a leaf image first.", "warning");
      return;
    }

    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<span class="ag-spinner ag-spinner-sm"></span> Analyzing...';

    if (progressBar) {
      progressBar.classList.remove("hidden");
      progressBar.style.display = ""; // clear any inline none
      progressBar.querySelector(".ag-progress-bar").style.width = "30%";
    }

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const farmId   = farmSelect.value;
      const cropType = document.getElementById("crop-type-input")?.value;
      const lat      = document.getElementById("lat-input")?.value;
      const lon      = document.getElementById("lon-input")?.value;
      const notes    = document.getElementById("notes-input")?.value;

      if (farmId)   formData.append("farm_id",  farmId);
      if (cropType) formData.append("crop_type", cropType);
      if (lat)      formData.append("latitude",  lat);
      if (lon)      formData.append("longitude", lon);
      if (notes)    formData.append("notes",     notes);

      if (progressBar) progressBar.querySelector(".ag-progress-bar").style.width = "60%";

      const result = await CropPulseAPI.disease.predict(formData);

      if (progressBar) progressBar.querySelector(".ag-progress-bar").style.width = "100%";

      // Store result and redirect to disease result page
      sessionStorage.setItem("ag_last_prediction", JSON.stringify(result));
      Utils.showToast("Analysis complete! Redirecting...", "success");
      setTimeout(() => { window.location.href = "/pages/disease-result.html"; }, 1000);

    } catch (err) {
      Utils.showToast(err.message || "Upload failed. Please try again.", "error");
      uploadBtn.disabled = false;
      uploadBtn.innerHTML = '🔬 Analyze Crop';
      if (progressBar) progressBar.classList.add("hidden");
    }
  });

  // ── Reset Button ────────────────────────────────────────────────────────
  document.getElementById("reset-btn")?.addEventListener("click", () => {
    selectedFile = null;
    fileInput.value = "";
    previewWrap?.classList.add("hidden");
    uploadBtn.disabled = true;
    const infoEl = document.getElementById("file-info");
    if (infoEl) infoEl.classList.add("hidden");
  });

  // ── Get Location ────────────────────────────────────────────────────────
  document.getElementById("get-location-btn")?.addEventListener("click", () => {
    if (!navigator.geolocation) {
      Utils.showToast("Geolocation not supported by your browser.", "warning");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      pos => {
        const latEl = document.getElementById("lat-input");
        const lonEl = document.getElementById("lon-input");
        if (latEl) latEl.value = pos.coords.latitude.toFixed(6);
        if (lonEl) lonEl.value = pos.coords.longitude.toFixed(6);
        Utils.showToast("Location captured!", "success");
      },
      () => Utils.showToast("Could not get location.", "error")
    );
  });
});
