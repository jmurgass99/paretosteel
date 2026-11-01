import * as THREE from "three";
import type { ParetoResult } from "../data-model.ts";

export function createParetoViewer3D(container: HTMLElement): {
  update: (res: ParetoResult, activeRoute: string) => void;
} {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x060a12);

  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
  camera.position.set(12, 8, 14);
  camera.lookAt(0, 0, 0);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  container.appendChild(renderer.domElement);

  const ambient = new THREE.AmbientLight(0xffffff, 0.72);
  const dir = new THREE.DirectionalLight(0xffffff, 0.9);
  dir.position.set(10, 15, 12);
  scene.add(ambient, dir);

  const group = new THREE.Group();
  scene.add(group);

  const resize = () => {
    const w = container.clientWidth || 640;
    const h = container.clientHeight || 480;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  };
  window.addEventListener("resize", resize);
  setTimeout(resize, 0);

  const animate = () => {
    requestAnimationFrame(animate);
    group.rotation.y += 0.003;
    renderer.render(scene, camera);
  };
  animate();

  return {
    update(res: ParetoResult, activeRoute: string) {
      while (group.children.length > 0) group.remove(group.children[0]);

      let routeColor = 0xf59e0b; // BF-BOF naranja
      if (activeRoute === "EAF") routeColor = 0x38bdf8; // EAF cyan
      if (activeRoute === "LOW_CARBON") routeColor = 0x10b981; // Green esmeralda

      const totalL = res.stations.reduce((acc, s) => acc + s.dxM, 0);
      const beamL = Math.max(totalL, 6);

      // Modelo 3D de Viga Doble T (I-beam)
      const mat = new THREE.MeshStandardMaterial({
        color: routeColor,
        metalness: 0.7,
        roughness: 0.35,
      });

      // Alma
      const webGeo = new THREE.BoxGeometry(beamL, 0.42, 0.015);
      const web = new THREE.Mesh(webGeo, mat);
      group.add(web);

      // Ala superior
      const fTopGeo = new THREE.BoxGeometry(beamL, 0.018, 0.22);
      const fTop = new THREE.Mesh(fTopGeo, mat);
      fTop.position.set(0, 0.21, 0);
      group.add(fTop);

      // Ala inferior
      const fBotGeo = new THREE.BoxGeometry(beamL, 0.018, 0.22);
      const fBot = new THREE.Mesh(fBotGeo, mat);
      fBot.position.set(0, -0.21, 0);
      group.add(fBot);

      // Soportes en apoyos
      const suppGeo = new THREE.ConeGeometry(0.25, 0.4, 4);
      const suppMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8 });
      const s1 = new THREE.Mesh(suppGeo, suppMat);
      s1.position.set(-beamL / 2, -0.42, 0);
      group.add(s1);

      const s2 = new THREE.Mesh(suppGeo, suppMat);
      s2.position.set(beamL / 2, -0.42, 0);
      group.add(s2);
    },
  };
}
