import { Component, Input, ElementRef, ViewChild, AfterViewInit, OnDestroy, OnChanges, ChangeDetectorRef } from '@angular/core';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import { ApiService } from '../../services/api';

@Component({
  selector: 'app-three-viewer',
  standalone: true,
  templateUrl: './three-viewer.html',
  styleUrl: './three-viewer.css',
})
export class ThreeViewerComponent implements AfterViewInit, OnDestroy, OnChanges {
  @Input() jobId = '';
  @ViewChild('canvas') canvasRef!: ElementRef<HTMLCanvasElement>;

  loading = false;
  meshGenerated = false;
  error = '';

  private renderer!: THREE.WebGLRenderer;
  private scene!: THREE.Scene;
  private camera!: THREE.PerspectiveCamera;
  private controls!: OrbitControls;
  private animationId = 0;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  private sceneReady = false;

  ngAfterViewInit() {
    this.tryInitScene();
  }

  ngOnChanges() {
    this.meshGenerated = false;
    this.error = '';
  }

  private tryInitScene() {
    const canvas = this.canvasRef?.nativeElement;
    if (!canvas) return;
    const w = canvas.parentElement?.clientWidth || 0;
    if (w > 0 && !this.sceneReady) {
      this.initScene();
      this.animate();
      this.sceneReady = true;
    }
  }

  ngOnDestroy() {
    cancelAnimationFrame(this.animationId);
    this.renderer?.dispose();
  }

  private initScene() {
    const canvas = this.canvasRef.nativeElement;
    const w = canvas.parentElement?.clientWidth || 800;
    const h = 500;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x1a1d27);

    this.camera = new THREE.PerspectiveCamera(60, w / h, 0.1, 10000);
    this.camera.position.set(0, 0, 300);

    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    this.renderer.setSize(w, h);
    this.renderer.setPixelRatio(window.devicePixelRatio);

    const ambient = new THREE.AmbientLight(0xffffff, 0.5);
    this.scene.add(ambient);

    const directional = new THREE.DirectionalLight(0xffffff, 0.8);
    directional.position.set(100, 200, 300);
    this.scene.add(directional);

    const backLight = new THREE.DirectionalLight(0xffffff, 0.3);
    backLight.position.set(-100, -200, -300);
    this.scene.add(backLight);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.05;
  }

  private animate() {
    this.animationId = requestAnimationFrame(() => this.animate());
    this.controls?.update();
    this.renderer?.render(this.scene, this.camera);
  }

  generateMesh() {
    if (!this.jobId) return;
    this.tryInitScene();
    this.loading = true;
    this.error = '';

    this.api.triggerMesh(this.jobId).subscribe({
      next: () => {
        this.meshGenerated = true;
        this.cdr.detectChanges();
        this.loadSTL();
      },
      error: (err) => {
        this.loading = false;
        this.error = err.error?.detail || 'Mesh generation failed';
        this.cdr.detectChanges();
      },
    });
  }

  private loadSTL() {
    const loader = new STLLoader();
    const url = this.api.getMeshUrl(this.jobId);

    loader.load(
      url,
      (geometry) => {
        geometry.computeVertexNormals();
        geometry.center();

        const material = new THREE.MeshPhongMaterial({
          color: new THREE.Color(252 / 255, 3 / 255, 115 / 255),
          specular: 0x444444,
          shininess: 40,
          side: THREE.DoubleSide,
        });

        const mesh = new THREE.Mesh(geometry, material);

        const box = new THREE.Box3().setFromObject(mesh);
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const scale = 200 / maxDim;
        mesh.scale.set(scale, scale, scale);

        const toRemove = this.scene.children.filter((c) => c instanceof THREE.Mesh);
        toRemove.forEach((m) => this.scene.remove(m));

        this.scene.add(mesh);
        this.camera.position.set(0, 0, 300);
        this.controls.reset();
        this.loading = false;
        this.cdr.detectChanges();
      },
      undefined,
      (err) => {
        this.loading = false;
        this.error = 'Failed to load 3D mesh file from server';
        this.cdr.detectChanges();
      }
    );
  }
}
