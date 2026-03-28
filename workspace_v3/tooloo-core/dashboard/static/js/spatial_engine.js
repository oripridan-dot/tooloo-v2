/**
 * 🛰️ Spatial Engine & Sensor Matrix
 * Part of the TooLoo-Core SOTA Dashboard
 */

const SensorMatrix = (() => {
  const state = {
    micVolume: 0, micLow: 0, micMid: 0, micHigh: 0,
    faceX: 0, faceY: 0, faceZ: 0, ambientLum: 0.5,
    micEnabled: false, camEnabled: false,
    fftData: null,
  };

  let _ctx = null, _analyser = null;
  const _fft = new Uint8Array(128);
  let _mouseX = 0, _mouseY = 0;

  document.addEventListener('mousemove', e => {
    _mouseX = (e.clientX / window.innerWidth) * 2 - 1;
    _mouseY = (e.clientY / window.innerHeight) * 2 - 1;
  });

  async function enableMic() {
    if (state.micEnabled) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
      _ctx = new (window.AudioContext || window.webkitAudioContext)();
      _analyser = _ctx.createAnalyser();
      _analyser.fftSize = 256;
      _ctx.createMediaStreamSource(stream).connect(_analyser);
      state.micEnabled = true;
      console.log('Microphone online');
    } catch (e) {
      console.warn('Mic access denied', e);
    }
  }

  function _tickMic() {
    if (!_analyser) return;
    _analyser.getByteFrequencyData(_fft);
    state.fftData = _fft;
    const N = _fft.length;
    let sum = 0, low = 0, mid = 0, high = 0;
    for (let i = 0; i < N; i++) {
      const v = _fft[i] / 255;
      sum += v;
      if (i < N * 0.15) low += v;
      else if (i < N * 0.50) mid += v;
      else high += v;
    }
    state.micVolume = sum / N;
    state.micLow = low / (N * 0.15);
    state.micMid = mid / (N * 0.35);
    state.micHigh = high / (N * 0.50);
  }

  function _tickCameraFallback() {
    state.faceX += (_mouseX - state.faceX) * 0.04;
    state.faceY += (_mouseY - state.faceY) * 0.04;
  }

  function tick() {
    _tickMic();
    _tickCameraFallback();
  }

  return { state, enableMic, tick };
})();

const SpatialEngine = (() => {
  let renderer, scene, camera, clock;
  let envGroup, dataGroup, glassGroup;
  let anchorMesh, wireMesh, anchorMat;
  let ptsMat;
  
  const ORB_DEFS = [
    { id: 'route', x: -3.4, y: 1.4, z: 0, color: 0x6c63ff, label: 'ROUTE' },
    { id: 'jit', x: -1.2, y: 2.2, z: 0, color: 0x00e5ff, label: 'JIT' },
    { id: 'tribunal', x: 1.2, y: 2.2, z: 0, color: 0xff4757, label: 'TRIBUNAL' },
    { id: 'scope', x: 3.4, y: 1.4, z: 0, color: 0xffab40, label: 'SCOPE' },
    { id: 'execute', x: -1.6, y: -0.9, z: 0, color: 0x2ed573, label: 'EXECUTE' },
    { id: 'refine', x: 1.6, y: -0.9, z: 0, color: 0xb388ff, label: 'REFINE' },
  ];

  const _orbMesh = {};
  const _orbMat = {};
  const _ringMat = {};
  const _tubeMats = [];

  function init(canvasId, containerId) {
    const canvas = document.getElementById(canvasId);
    const container = document.getElementById(containerId);
    if (!canvas || !container) return;

    renderer = new THREE.WebGLRenderer({
      canvas, antialias: true, alpha: true, powerPreference: 'high-performance',
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.28;

    scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x080810, 0.036);

    camera = new THREE.PerspectiveCamera(55, container.clientWidth / container.clientHeight, 0.1, 200);
    camera.position.set(0, 0.2, 7);

    clock = new THREE.Clock();

    // Environment
    envGroup = new THREE.Group();
    envGroup.position.z = -4;
    scene.add(envGroup);

    const ambLight = new THREE.AmbientLight(0x0d0d20, 0.7);
    const rimLight = new THREE.PointLight(0x00e5ff, 1.5, 40);
    rimLight.position.set(-7, 5, 2);
    scene.add(ambLight, rimLight);

    // Data Logic Layer
    dataGroup = new THREE.Group();
    scene.add(dataGroup);

    ORB_DEFS.forEach(def => {
      const geo = new THREE.SphereGeometry(0.24, 32, 32);
      const mat = new THREE.MeshStandardMaterial({
        color: def.color, emissive: new THREE.Color(def.color),
        emissiveIntensity: 0.4, roughness: 0.18, metalness: 0.65,
        transparent: true, opacity: 0.94,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(def.x, def.y, def.z);
      dataGroup.add(mesh);
      _orbMesh[def.id] = mesh;
      _orbMat[def.id] = mat;
    });

    // Anchor
    const anchorGeo = new THREE.IcosahedronGeometry(0.42, 3);
    anchorMat = new THREE.MeshStandardMaterial({
      color: 0x6c63ff, emissive: new THREE.Color(0x6c63ff),
      emissiveIntensity: 0.8, roughness: 0.12, metalness: 0.85,
    });
    anchorMesh = new THREE.Mesh(anchorGeo, anchorMat);
    anchorMesh.position.set(0, 0.3, 0.6);
    dataGroup.add(anchorMesh);

    const wireGeo = new THREE.IcosahedronGeometry(0.54, 1);
    const wireMat = new THREE.MeshBasicMaterial({ color: 0x6c63ff, wireframe: true, transparent: true, opacity: 0.17 });
    wireMesh = new THREE.Mesh(wireGeo, wireMat);
    wireMesh.position.copy(anchorMesh.position);
    dataGroup.add(wireMesh);

    window.addEventListener('resize', () => {
      const w = container.clientWidth, h = container.clientHeight;
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    });

    animate();
  }

  function animate() {
    requestAnimationFrame(animate);
    const t = clock.getElapsedTime();
    SensorMatrix.tick();
    const s = SensorMatrix.state;

    // Pulse effects
    anchorMat.emissiveIntensity = 0.7 + s.micVolume * 1.5 + Math.sin(t * 1.2) * 0.15;
    wireMesh.rotation.y = t * 0.26;
    
    ORB_DEFS.forEach((def, i) => {
      const mesh = _orbMesh[def.id];
      mesh.position.y = def.y + Math.sin(t * 0.72 + i) * 0.09;
    });

    renderer.render(scene, camera);
  }

  function pulseOrb(id, status) {
    const mat = _orbMat[id];
    if (!mat || !window.gsap) return;
    const INTENS = { active: 0.95, done: 1.3, fail: 0.08, idle: 0.4 };
    gsap.to(mat, { emissiveIntensity: INTENS[status] ?? 0.4, duration: 0.38, ease: 'power2.out' });
  }

  return { init, pulseOrb };
})();

window.SensorMatrix = SensorMatrix;
window.SpatialEngine = SpatialEngine;
