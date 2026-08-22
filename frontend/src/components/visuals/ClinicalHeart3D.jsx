import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

function makeHeartGeometry() {
  const shape = new THREE.Shape();
  const x = 0;
  const y = 0;
  shape.moveTo(x, y + 0.25);
  shape.bezierCurveTo(x - 0.55, y + 0.95, x - 1.35, y + 0.62, x - 1.35, y - 0.05);
  shape.bezierCurveTo(x - 1.35, y - 0.65, x - 0.72, y - 1.1, x, y - 1.72);
  shape.bezierCurveTo(x + 0.72, y - 1.1, x + 1.35, y - 0.65, x + 1.35, y - 0.05);
  shape.bezierCurveTo(x + 1.35, y + 0.62, x + 0.55, y + 0.95, x, y + 0.25);
  const geometry = new THREE.ExtrudeGeometry(shape, { depth: 0.62, bevelEnabled: true, bevelSegments: 5, bevelSize: 0.13, bevelThickness: 0.14, curveSegments: 14 });
  geometry.center();
  geometry.rotateZ(Math.PI);
  geometry.rotateX(-0.18);
  return geometry;
}

export function ClinicalHeart3D() {
  const mountRef = useRef(null);
  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return undefined;
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0xd9f5ff, 0.035);
    const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);
    camera.position.set(0, 0, 7.2);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    mount.appendChild(renderer.domElement);

    const root = new THREE.Group();
    scene.add(root);
    const heart = new THREE.Mesh(makeHeartGeometry(), new THREE.MeshPhysicalMaterial({ color: 0xef5276, roughness: 0.2, metalness: 0.05, clearcoat: 0.8, clearcoatRoughness: 0.18, emissive: 0x601d39, emissiveIntensity: 0.36 }));
    heart.scale.setScalar(1.15);
    root.add(heart);
    const wire = new THREE.Mesh(heart.geometry.clone(), new THREE.MeshBasicMaterial({ color: 0xffd5df, wireframe: true, transparent: true, opacity: 0.12 }));
    wire.scale.setScalar(1.035);
    root.add(wire);

    const ringGroup = new THREE.Group();
    root.add(ringGroup);
    [1.55, 1.9, 2.25].forEach((radius, index) => {
      const ring = new THREE.Mesh(new THREE.TorusGeometry(radius, index === 1 ? 0.018 : 0.011, 10, 100), new THREE.MeshBasicMaterial({ color: index === 1 ? 0x0ea5e9 : 0x7dd3fc, transparent: true, opacity: index === 1 ? 0.8 : 0.48 }));
      ring.rotation.set(index === 0 ? 0.9 : index === 1 ? 0.1 : 1.35, index === 2 ? 0.72 : 0.15, index * 0.8);
      ringGroup.add(ring);
    });

    const particleCount = 180;
    const particlePositions = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount; i += 1) {
      const radius = 2.55 + Math.random() * 1.35;
      const angle = Math.random() * Math.PI * 2;
      particlePositions[i * 3] = Math.cos(angle) * radius;
      particlePositions[i * 3 + 1] = (Math.random() - 0.5) * 3.8;
      particlePositions[i * 3 + 2] = Math.sin(angle) * radius * 0.42;
    }
    const particlesGeometry = new THREE.BufferGeometry();
    particlesGeometry.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
    const particles = new THREE.Points(particlesGeometry, new THREE.PointsMaterial({ color: 0x38bdf8, size: 0.035, transparent: true, opacity: 0.75, sizeAttenuation: true }));
    scene.add(particles);

    scene.add(new THREE.HemisphereLight(0xffffff, 0x7dd3fc, 2.2));
    const keyLight = new THREE.PointLight(0xffffff, 32, 14); keyLight.position.set(3, 3, 5); scene.add(keyLight);
    const fillLight = new THREE.PointLight(0x38bdf8, 18, 12); fillLight.position.set(-4, -1, 2); scene.add(fillLight);
    const rimLight = new THREE.PointLight(0xfda4af, 12, 10); rimLight.position.set(2, -3, -2); scene.add(rimLight);

    const pointer = { x: 0, y: 0 };
    const onPointerMove = (event) => { const rect = mount.getBoundingClientRect(); pointer.x = ((event.clientX - rect.left) / rect.width - 0.5) * 2; pointer.y = ((event.clientY - rect.top) / rect.height - 0.5) * 2; };
    mount.addEventListener('pointermove', onPointerMove);
    const resize = () => { const width = mount.clientWidth || 280; const height = mount.clientHeight || 280; camera.aspect = width / height; camera.updateProjectionMatrix(); renderer.setSize(width, height, false); };
    resize();
    const clock = new THREE.Clock();
    let frame;
    const animate = () => {
      const elapsed = clock.getElapsedTime();
      const beat = 1 + Math.max(0, Math.sin(elapsed * 4.8)) * 0.045;
      heart.scale.setScalar(1.15 * beat);
      wire.scale.setScalar(1.035 * beat);
      root.rotation.y += (pointer.x * 0.22 - root.rotation.y) * 0.035;
      root.rotation.x += (-pointer.y * 0.12 - root.rotation.x) * 0.035;
      ringGroup.rotation.z = elapsed * 0.15;
      ringGroup.rotation.y = elapsed * 0.08;
      particles.rotation.y = elapsed * 0.025;
      particles.rotation.x = Math.sin(elapsed * 0.2) * 0.08;
      renderer.render(scene, camera);
      frame = requestAnimationFrame(animate);
    };
    animate();
    return () => { cancelAnimationFrame(frame); mount.removeEventListener('pointermove', onPointerMove); renderer.dispose(); heart.geometry.dispose(); heart.material.dispose(); wire.geometry.dispose(); wire.material.dispose(); particlesGeometry.dispose(); particles.material.dispose(); ringGroup.children.forEach((ring) => { ring.geometry.dispose(); ring.material.dispose(); }); if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement); };
  }, []);

  return <div ref={mountRef} className="clinical-heart-3d" aria-label="Interactive 3D heart visualization" />;
}
