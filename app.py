import socket
import math
import time
import random
from flask import Flask, render_template_string, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

PLAYERS = {}
QUEUE = []
MATCHES = {}
BOT_MATCHES = {}

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>3D Ultra Rivals Arena - Daytime & Advanced Bot</title>
    <style>
        * { box-sizing: border-box; touch-action: none; user-select: none; -webkit-user-select: none; }
        body { margin: 0; overflow: hidden; background: #87ceeb; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        #canvas-container { width: 100vw; height: 100vh; }
        
        #device-screen {
            position: absolute; inset: 0; background: #0b0f19;
            display: flex; flex-direction: column; justify-content: center; align-items: center;
            color: white; z-index: 100; text-align: center; padding: 20px;
        }
        .mode-cards { display: flex; gap: 15px; margin-top: 20px; flex-wrap: wrap; justify-content: center; }
        .mode-card {
            background: #1e293b; border: 2px solid #334155; padding: 20px 30px; border-radius: 16px;
            cursor: pointer; transition: transform 0.2s, border-color 0.2s; min-width: 140px; color: white;
        }
        .mode-card:hover, .mode-card:active { transform: translateY(-4px); border-color: #38bdf8; }

        .color-picker { display: flex; gap: 12px; margin-top: 15px; }
        .color-dot { width: 36px; height: 36px; border-radius: 50%; border: 2px solid #fff; cursor: pointer; transition: transform 0.2s; }
        .color-dot.selected { transform: scale(1.25); border-color: #38bdf8; }

        #match-result-overlay {
            position: absolute; inset: 0;
            display: none; flex-direction: column; justify-content: center; align-items: center;
            z-index: 90; text-align: center; background: rgba(11, 15, 25, 0.85);
            backdrop-filter: blur(4px); pointer-events: none;
        }
        #result-title { font-size: 4rem; font-weight: 900; letter-spacing: 4px; margin: 0; text-shadow: 0 0 20px rgba(0,0,0,0.8); }

        /* Crosshair */
        #crosshair {
            position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
            width: 12px; height: 12px; pointer-events: none; z-index: 10;
            transition: opacity 0.15s, transform 0.15s;
        }
        #crosshair::before, #crosshair::after { content: ''; position: absolute; background: rgba(0, 0, 0, 0.85); }
        #crosshair::before { top: 5px; left: -8px; width: 28px; height: 2px; }
        #crosshair::after { top: -8px; left: 5px; width: 2px; height: 28px; }
        #crosshair.ads-active { opacity: 0.2; transform: translate(-50%, -50%) scale(0.6); }
        .hit-marker::before, .hit-marker::after { background: #ef4444 !important; }

        #damage-vignette {
            position: absolute; inset: 0; pointer-events: none; z-index: 8;
            box-shadow: inset 0 0 50px rgba(239, 68, 68, 0); transition: box-shadow 0.1s;
        }
        #damage-vignette.active { box-shadow: inset 0 0 80px rgba(239, 68, 68, 0.8); }

        #hud {
            position: absolute; top: 15px; left: 15px;
            color: #0f172a; font-weight: bold; font-size: 1rem;
            text-shadow: 1px 1px 2px rgba(255,255,255,0.8); z-index: 10; pointer-events: none;
        }
        .bar-bg { width: 160px; height: 14px; background: rgba(0,0,0,0.3); border: 2px solid #0f172a; border-radius: 8px; overflow: hidden; margin-top: 4px; }
        .bar-fill { width: 100%; height: 100%; background: #22c55e; transition: width 0.1s; }

        #queue-status {
            position: absolute; top: 15px; left: 50%; transform: translateX(-50%);
            background: rgba(255, 255, 255, 0.85); border: 2px solid #0284c7; color: #0284c7;
            padding: 8px 18px; border-radius: 20px; font-weight: bold; z-index: 10; font-size: 0.9rem; pointer-events: none;
        }

        #mouse-tip {
            position: absolute; bottom: 15px; left: 15px;
            background: rgba(15, 23, 42, 0.75); color: white;
            padding: 6px 12px; border-radius: 8px; font-size: 0.8rem; font-weight: bold; z-index: 30; pointer-events: none;
        }

        #bot-btn {
            position: absolute; top: 60px; left: 50%; transform: translateX(-50%);
            background: #8b5cf6; border: 2px solid #c084fc; color: white;
            padding: 10px 20px; border-radius: 12px; font-weight: bold; z-index: 30;
            cursor: pointer; transition: transform 0.2s, background 0.2s; pointer-events: auto;
        }
        #bot-btn:hover { transform: translateX(-50%) scale(1.05); background: #7c3aed; }

        #weapon-selector {
            position: absolute; top: 15px; right: 15px; color: white; z-index: 30; display: flex; gap: 4px; pointer-events: auto; flex-wrap: wrap; max-width: 280px; justify-content: flex-end;
        }
        .weapon-card {
            background: rgba(15, 23, 42, 0.8); border: 2px solid #334155;
            padding: 6px 10px; border-radius: 8px; font-weight: bold; font-size: 0.75rem; cursor: pointer;
        }
        .weapon-card.active { border-color: #38bdf8; background: rgba(14, 165, 233, 0.3); }

        #touch-controls { display: none; position: absolute; inset: 0; pointer-events: auto; z-index: 20; }
        #joystick-zone {
            position: absolute; bottom: 30px; left: 30px; width: 120px; height: 120px;
            background: rgba(255,255,255,0.2); border: 2px solid rgba(255,255,255,0.5);
            border-radius: 50%; pointer-events: auto; z-index: 25;
        }
        #joystick-knob {
            position: absolute; top: 40px; left: 40px; width: 40px; height: 40px;
            background: #0284c7; border-radius: 50%; pointer-events: none;
        }

        .mobile-btn {
            position: absolute; pointer-events: auto; background: rgba(15, 23, 42, 0.85);
            border: 2px solid rgba(255,255,255,0.4); color: white; border-radius: 50%;
            display: flex; justify-content: center; align-items: center; font-weight: bold; z-index: 25;
        }
        #shoot-btn { bottom: 40px; right: 40px; width: 80px; height: 80px; background: rgba(239, 68, 68, 0.8); font-size: 1.4rem; }
        #aim-btn { bottom: 135px; right: 115px; width: 60px; height: 60px; font-size: 1rem; background: rgba(168, 85, 247, 0.7); }
        #jump-btn { bottom: 135px; right: 35px; width: 60px; height: 60px; font-size: 1rem; }
        #slide-btn { bottom: 40px; right: 135px; width: 60px; height: 60px; font-size: 1rem; background: rgba(56, 189, 248, 0.6); }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.socket.io/4.7.2/socket.io.min.js"></script>
</head>
<body>

    <div id="damage-vignette"></div>

    <div id="device-screen">
        <h1 style="font-size: 2.5rem; margin: 0;">ULTRA RIVALS 3D</h1>
        <p style="color: #94a3b8; margin-top: 6px;">Select Suit Color:</p>
        
        <div class="color-picker">
            <div class="color-dot selected" style="background:#ef4444" onclick="selectColor(0xef4444, this)"></div>
            <div class="color-dot" style="background:#3b82f6" onclick="selectColor(0x3b82f6, this)"></div>
            <div class="color-dot" style="background:#10b981" onclick="selectColor(0x10b981, this)"></div>
            <div class="color-dot" style="background:#8b5cf6" onclick="selectColor(0x8b5cf6, this)"></div>
            <div class="color-dot" style="background:#facc15" onclick="selectColor(0xfacc15, this)"></div>
        </div>

        <p style="color: #94a3b8; margin-top: 15px;">Select Controls:</p>
        <div class="mode-cards">
            <button class="mode-card" onclick="selectControlMode('pc')">
                <div style="font-size: 2.2rem;">💻</div>
                <b>PC / Keyboard</b>
            </button>
            <button class="mode-card" onclick="selectControlMode('mobile')" ontouchstart="selectControlMode('mobile')">
                <div style="font-size: 2.2rem;">📱</div>
                <b>Phone / Touch</b>
            </button>
        </div>
    </div>

    <div id="match-result-overlay">
        <h1 id="result-title">VICTORY</h1>
        <div style="font-size: 1.2rem; color: #94a3b8; margin-top: 10px; font-weight: bold;">Returning to lobby...</div>
    </div>

    <div id="crosshair"></div>

    <div id="hud">
        <div id="locationTag" style="color: #0284c7;">LOCATION: LOBBY</div>
        <div class="bar-bg"><div id="healthFill" class="bar-fill"></div></div>
        <div id="scoreDisplay" style="margin-top: 5px; font-size: 0.85rem; color: #d97706;">Kills: 0 | Deaths: 0</div>
        <div id="buffDisplay" style="margin-top: 4px; font-size: 0.75rem; color: #0284c7;"></div>
    </div>

    <div id="queue-status">LOBBY PRACTICE AREA</div>
    <div id="mouse-tip">Press 'V' to Toggle Mouse Lock</div>
    <button id="bot-btn" onclick="startBotMatch()" ontouchstart="startBotMatch()">🤖 PLAY VS BOT</button>

    <div id="weapon-selector">
        <div id="wep-0" class="weapon-card active" onclick="switchWeapon(0)" ontouchstart="switchWeapon(0)">1. Rifle</div>
        <div id="wep-1" class="weapon-card" onclick="switchWeapon(1)" ontouchstart="switchWeapon(1)">2. Shotgun</div>
        <div id="wep-2" class="weapon-card" onclick="switchWeapon(2)" ontouchstart="switchWeapon(2)">3. Sniper</div>
        <div id="wep-3" class="weapon-card" onclick="switchWeapon(3)" ontouchstart="switchWeapon(3)">4. Rocket</div>
        <div id="wep-4" class="weapon-card" onclick="switchWeapon(4)" ontouchstart="switchWeapon(4)">5. Grapple</div>
    </div>

    <div id="touch-controls">
        <div id="joystick-zone"><div id="joystick-knob"></div></div>
        <div id="shoot-btn" class="mobile-btn">🔥</div>
        <div id="aim-btn" class="mobile-btn">🎯</div>
        <div id="jump-btn" class="mobile-btn">⬆️</div>
        <div id="slide-btn" class="mobile-btn">💨</div>
    </div>

    <div id="canvas-container"></div>

    <script>
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        let audioCtx = null;

        function initAudio() { if (!audioCtx) audioCtx = new AudioContext(); }

        function playSound(type) {
            if (!audioCtx) return;
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.connect(gain); gain.connect(audioCtx.destination);
            const now = audioCtx.currentTime;

            if (type === 'rifle') {
                osc.type = 'sawtooth'; osc.frequency.setValueAtTime(320, now);
                osc.frequency.exponentialRampToValueAtTime(80, now + 0.1);
                gain.gain.setValueAtTime(0.3, now); gain.gain.linearRampToValueAtTime(0.01, now + 0.1);
                osc.start(now); osc.stop(now + 0.1);
            } else if (type === 'shotgun') {
                osc.type = 'square'; osc.frequency.setValueAtTime(160, now);
                osc.frequency.exponentialRampToValueAtTime(30, now + 0.2);
                gain.gain.setValueAtTime(0.5, now); gain.gain.linearRampToValueAtTime(0.01, now + 0.2);
                osc.start(now); osc.stop(now + 0.2);
            } else if (type === 'sniper') {
                osc.type = 'triangle'; osc.frequency.setValueAtTime(650, now);
                osc.frequency.exponentialRampToValueAtTime(40, now + 0.3);
                gain.gain.setValueAtTime(0.6, now); gain.gain.linearRampToValueAtTime(0.01, now + 0.3);
                osc.start(now); osc.stop(now + 0.3);
            } else if (type === 'rocket') {
                osc.type = 'sawtooth'; osc.frequency.setValueAtTime(110, now);
                osc.frequency.linearRampToValueAtTime(20, now + 0.4);
                gain.gain.setValueAtTime(0.7, now); gain.gain.linearRampToValueAtTime(0.01, now + 0.4);
                osc.start(now); osc.stop(now + 0.4);
            } else if (type === 'hit') {
                osc.type = 'sine'; osc.frequency.setValueAtTime(880, now);
                gain.gain.setValueAtTime(0.2, now); gain.gain.linearRampToValueAtTime(0.01, now + 0.08);
                osc.start(now); osc.stop(now + 0.08);
            } else if (type === 'jump') {
                osc.type = 'sine'; osc.frequency.setValueAtTime(200, now);
                osc.frequency.exponentialRampToValueAtTime(450, now + 0.15);
                gain.gain.setValueAtTime(0.2, now); gain.gain.linearRampToValueAtTime(0.01, now + 0.15);
                osc.start(now); osc.stop(now + 0.15);
            }
        }

        const socket = io({ transports: ['polling', 'websocket'], upgrade: true, autoConnect: true });

        let myId = null, players = {}, otherMeshMap = {}, otherAnimMap = {};
        let scene, camera, renderer, pitchObject, yawObject;
        let keys = {}, isMobile = false;

        let isAiming = false, currentFov = 75, targetFov = 75;
        let fpRigGroup, currentFpGunMesh = null;
        let fpRecoil = 0, fpBobTimer = 0;

        let isGrounded = false, velocityY = 0, jumpCount = 0;
        let isSliding = false, slideTimer = 0;
        let speedBoostTime = 0;
        const GRAVITY = -26, JUMP_FORCE = 11;

        let obstacles = [], jumpPads = [], powerUps = [], activeRockets = [], particles = [];
        let targetDummies = [];
        let teleporterRingMesh = null;
        let inQueue = false, inBotMatch = false, myColor = 0xef4444;

        // Upgraded Bot State Management
        let activeBotMesh = null;
        let botLastShootTime = 0;
        let botStrafeDir = 1;
        let botStrafeTimer = 0;
        let botJumpTimer = 0;
        let botYVelocity = 0;
        let botTrickshotState = 0; // 0: Normal, 1: Spinning, 2: Shooting

        const WEAPONS = [
            { name: "Rifle", damage: 18, cooldown: 110, spread: 0.02, hipPos: [0.28, -0.25, -0.45], adsPos: [0, -0.18, -0.3] },
            { name: "Shotgun", damage: 11, pellets: 7, cooldown: 650, spread: 0.09, hipPos: [0.28, -0.28, -0.5], adsPos: [0, -0.2, -0.35] },
            { name: "Sniper", damage: 75, cooldown: 950, spread: 0.001, hipPos: [0.3, -0.25, -0.55], adsPos: [0, -0.16, -0.25] },
            { name: "Rocket", damage: 80, cooldown: 1200, isRocket: true, hipPos: [0.32, -0.3, -0.6], adsPos: [0, -0.2, -0.4] },
            { name: "Grapple", damage: 5, cooldown: 400, isGrapple: true, hipPos: [0.25, -0.22, -0.4], adsPos: [0, -0.15, -0.3] }
        ];
        let currentWepIdx = 0, lastShootTime = 0;

        function startBotMatch() {
            if (inQueue || inBotMatch) return;
            if (document.pointerLockElement) document.exitPointerLock();
            socket.emit('start_bot_match');
        }

        function togglePointerLock() {
            if (isMobile) return;
            if (document.pointerLockElement === document.body) {
                document.exitPointerLock();
            } else {
                document.body.requestPointerLock();
            }
        }

        function selectColor(color, el) {
            myColor = color;
            document.querySelectorAll('.color-dot').forEach(d => d.classList.remove('selected'));
            el.classList.add('selected');
        }

        function selectControlMode(mode) {
            initAudio();
            isMobile = (mode === 'mobile');
            document.getElementById('device-screen').style.display = 'none';
            if (isMobile) {
                document.getElementById('touch-controls').style.display = 'block';
                document.getElementById('mouse-tip').style.display = 'none';
            } else if (document.body.requestPointerLock) {
                document.body.requestPointerLock();
            }
            socket.emit('set_color', { color: myColor });
            onWindowResize();
        }

        function createFirstPersonRig() {
            fpRigGroup = new THREE.Group();
            
            const armMat = new THREE.MeshStandardMaterial({ color: 0xfca5a5, roughness: 0.7 });
            const sleeveMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.5 });

            const rArm = new THREE.Group();
            const rSleeveMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.35, 8), sleeveMat);
            rSleeveMesh.position.set(0, 0, 0); rSleeveMesh.rotation.x = Math.PI / 3;
            const rHandMesh = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.08, 0.12), armMat);
            rHandMesh.position.set(0, -0.12, -0.15);
            rArm.add(rSleeveMesh, rHandMesh);
            rArm.position.set(0.12, -0.05, 0.08);

            const lArm = new THREE.Group();
            const lSleeveMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.35, 8), sleeveMat);
            lSleeveMesh.position.set(0, 0, 0); lSleeveMesh.rotation.x = Math.PI / 3.5; lSleeveMesh.rotation.z = -Math.PI / 8;
            const lHandMesh = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.08, 0.12), armMat);
            lHandMesh.position.set(0.05, -0.1, -0.15);
            lArm.add(lSleeveMesh, lHandMesh);
            lArm.position.set(-0.22, -0.05, 0.08);

            fpRigGroup.add(rArm, lArm);
            camera.add(fpRigGroup);

            updateFpsGunModel();
        }

        function updateFpsGunModel() {
            if (currentFpGunMesh) fpRigGroup.remove(currentFpGunMesh);

            const wepGroup = new THREE.Group();
            const darkMat = new THREE.MeshStandardMaterial({ color: 0x1f2937, roughness: 0.3 });
            const metalMat = new THREE.MeshStandardMaterial({ color: 0x475569, metalness: 0.8, roughness: 0.2 });

            if (currentWepIdx === 0) {
                const body = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.1, 0.45), darkMat);
                const barrel = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.3, 8), metalMat);
                barrel.rotation.x = Math.PI / 2; barrel.position.set(0, 0.02, -0.3);
                const sight = new THREE.Mesh(new THREE.BoxGeometry(0.02, 0.04, 0.02), metalMat);
                sight.position.set(0, 0.06, -0.15);
                wepGroup.add(body, barrel, sight);
            } else if (currentWepIdx === 1) {
                const body = new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.11, 0.4), darkMat);
                const barrel1 = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.35, 8), metalMat);
                barrel1.rotation.x = Math.PI / 2; barrel1.position.set(-0.02, 0.03, -0.3);
                const barrel2 = barrel1.clone(); barrel2.position.x = 0.02;
                wepGroup.add(body, barrel1, barrel2);
            } else if (currentWepIdx === 2) {
                const body = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.09, 0.6), darkMat);
                const scope = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.2, 12), metalMat);
                scope.rotation.x = Math.PI / 2; scope.position.set(0, 0.07, -0.1);
                const longBarrel = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.45, 8), metalMat);
                longBarrel.rotation.x = Math.PI / 2; longBarrel.position.set(0, 0.01, -0.45);
                wepGroup.add(body, scope, longBarrel);
            } else if (currentWepIdx === 3) {
                const tube = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 0.65, 12), darkMat);
                tube.rotation.x = Math.PI / 2;
                const frontRing = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 0.08, 12), metalMat);
                frontRing.rotation.x = Math.PI / 2; frontRing.position.z = -0.3;
                wepGroup.add(tube, frontRing);
            } else if (currentWepIdx === 4) {
                const body = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.1, 0.35), darkMat);
                const hookHead = new THREE.Mesh(new THREE.ConeGeometry(0.05, 0.12, 4), metalMat);
                hookHead.rotation.x = -Math.PI / 2; hookHead.position.z = -0.22;
                wepGroup.add(body, hookHead);
            }

            currentFpGunMesh = wepGroup;
            fpRigGroup.add(currentFpGunMesh);
        }

        function createEnemyMesh(id, colorHex) {
            const group = new THREE.Group();
            const suitMat = new THREE.MeshStandardMaterial({ color: colorHex || 0xef4444, roughness: 0.4 });
            const darkMat = new THREE.MeshStandardMaterial({ color: 0x1f2937 });

            const torso = new THREE.Mesh(new THREE.BoxGeometry(0.8, 1.0, 0.45), suitMat);
            torso.position.y = 1.1; torso.userData.playerId = id; group.add(torso);

            const headGroup = new THREE.Group();
            const head = new THREE.Mesh(new THREE.BoxGeometry(0.45, 0.45, 0.45), suitMat);
            const visor = new THREE.Mesh(new THREE.BoxGeometry(0.4, 0.15, 0.1), new THREE.MeshBasicMaterial({ color: 0x38bdf8 }));
            visor.position.set(0, 0.05, -0.22);
            headGroup.add(head, visor);
            headGroup.position.y = 1.85; headGroup.userData.playerId = id; group.add(headGroup);

            const lLeg = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.8, 0.3), darkMat);
            lLeg.position.set(-0.22, 0.4, 0); lLeg.userData.playerId = id; group.add(lLeg);

            const rLeg = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.8, 0.3), darkMat);
            rLeg.position.set(0.22, 0.4, 0); rLeg.userData.playerId = id; group.add(rLeg);

            const enemyGun = new THREE.Mesh(new THREE.BoxGeometry(0.12, 0.15, 0.6), darkMat);
            enemyGun.position.set(0.45, 1.1, -0.3); enemyGun.userData.playerId = id; group.add(enemyGun);

            scene.add(group);
            otherMeshMap[id] = torso;
            otherAnimMap[id] = { group: group, lLeg: lLeg, rLeg: rLeg, head: headGroup };
            return group;
        }

        function createTargetDummy(x, y, z) {
            const group = new THREE.Group();
            group.position.set(x, y, z);

            const mat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, roughness: 0.3, metalness: 0.2 });
            const body = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.4, 1.4, 12), mat);
            body.position.y = 0.7; body.userData.isDummy = true;

            const ring1 = new THREE.Mesh(new THREE.TorusGeometry(0.42, 0.04, 8, 24), new THREE.MeshBasicMaterial({ color: 0xef4444 }));
            ring1.rotation.x = Math.PI/2; ring1.position.y = 0.7;

            const head = new THREE.Mesh(new THREE.SphereGeometry(0.3, 12, 12), mat);
            head.position.y = 1.6; head.userData.isDummy = true;

            group.add(body, ring1, head);
            scene.add(group);

            targetDummies.push({ group: group, baseY: y, hitTime: 0 });
            otherMeshMap["dummy_" + targetDummies.length] = body;
            otherMeshMap["dummy_head_" + targetDummies.length] = head;
        }

        function init3D() {
            const container = document.getElementById('canvas-container');
            
            scene = new THREE.Scene();
            // Daytime Sky Color
            scene.background = new THREE.Color(0x7dd3fc);
            scene.fog = new THREE.FogExp2(0xbae6fd, 0.005);

            camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);

            pitchObject = new THREE.Object3D();
            pitchObject.add(camera);
            yawObject = new THREE.Object3D();
            yawObject.position.set(0, 2, 100);
            yawObject.add(pitchObject);
            scene.add(yawObject);

            // Daytime Bright Lighting
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.85);
            scene.add(ambientLight);
            const sunLight = new THREE.DirectionalLight(0xfff7ed, 1.2);
            sunLight.position.set(30, 80, 50);
            scene.add(sunLight);

            createFirstPersonRig();

            // --- CYBERPUNK HIGH-TECH LOBBY DESIGN ---
            const lobbyFloorBase = new THREE.Mesh(
                new THREE.CylinderGeometry(32, 34, 1, 32),
                new THREE.MeshStandardMaterial({ color: 0x0284c7, roughness: 0.3, metalness: 0.8 })
            );
            lobbyFloorBase.position.set(0, -0.5, 100);
            scene.add(lobbyFloorBase);

            const lobbyFloorInner = new THREE.Mesh(
                new THREE.CylinderGeometry(30, 30, 0.2, 32),
                new THREE.MeshStandardMaterial({ color: 0xf8fafc, roughness: 0.5 })
            );
            lobbyFloorInner.position.set(0, 0.05, 100);
            scene.add(lobbyFloorInner);

            const lobbyGrid = new THREE.GridHelper(60, 30, 0x0284c7, 0xc2410c);
            lobbyGrid.position.set(0, 0.1, 100);
            scene.add(lobbyGrid);

            // Queue Teleporter Pad
            const padBase = new THREE.Mesh(
                new THREE.CylinderGeometry(4.5, 5, 0.4, 32),
                new THREE.MeshStandardMaterial({ color: 0x0284c7, metalness: 0.9, roughness: 0.1 })
            );
            padBase.position.set(0, 0.2, 86); scene.add(padBase);

            teleporterRingMesh = new THREE.Mesh(
                new THREE.TorusGeometry(4.2, 0.1, 8, 32),
                new THREE.MeshBasicMaterial({ color: 0x38bdf8 })
            );
            teleporterRingMesh.rotation.x = Math.PI / 2;
            teleporterRingMesh.position.set(0, 0.45, 86);
            scene.add(teleporterRingMesh);

            const spotLight = new THREE.SpotLight(0x38bdf8, 3, 30, Math.PI / 4, 0.5);
            spotLight.position.set(0, 15, 86);
            spotLight.target = padBase;
            scene.add(spotLight);

            // Invisible Circular Lobby Barrier Visual Rings
            const boundaryRing = new THREE.Mesh(
                new THREE.CylinderGeometry(30, 30, 10, 32, 1, true),
                new THREE.MeshPhysicalMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.12, side: THREE.DoubleSide })
            );
            boundaryRing.position.set(0, 5, 100);
            scene.add(boundaryRing);

            // Target Practice Area
            createTargetDummy(-8, 0.5, 112);
            createTargetDummy(0, 0.5, 115);
            createTargetDummy(8, 0.5, 112);

            // --- COMPACT 1v1 COMBAT ARENA (ISOLATED AT Z = 0) ---
            const arenaFloor = new THREE.Mesh(
                new THREE.PlaneGeometry(70, 70),
                new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.8 })
            );
            arenaFloor.rotation.x = -Math.PI / 2;
            scene.add(arenaFloor);

            const arenaGrid = new THREE.GridHelper(70, 35, 0x0284c7, 0x64748b);
            arenaGrid.position.y = 0.01;
            scene.add(arenaGrid);

            // ARENA PERIMETER WALLS (COMPACT BOUNDARIES)
            createObstacle(0, 5, -35, 70, 10, 2, 0x1e293b); // Back North
            createObstacle(0, 5, 35, 70, 10, 2, 0x1e293b);  // South Isolation Wall
            createObstacle(-35, 5, 0, 2, 10, 70, 0x1e293b); // West
            createObstacle(35, 5, 0, 2, 10, 70, 0x1e293b);  // East

            // Arena Cover & Obstacles
            createObstacle(0, 3, 0, 6, 6, 6, 0x0284c7);
            createObstacle(-12, 3, -10, 4, 6, 4, 0x10b981);
            createObstacle(12, 3, -10, 4, 6, 4, 0x10b981);
            createObstacle(-15, 4, 15, 6, 8, 6, 0x8b5cf6);
            createObstacle(15, 4, 15, 6, 8, 6, 0x8b5cf6);

            createJumpPad(-12, 0.2, 5); createJumpPad(12, 0.2, 5);
            createPowerUp(-15, 1.5, -5, 'health'); createPowerUp(15, 1.5, -5, 'speed');

            renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setPixelRatio(window.devicePixelRatio);
            container.appendChild(renderer.domElement);

            window.addEventListener('resize', onWindowResize);
        }

        function createObstacle(x, y, z, w, h, d, color) {
            const mesh = new THREE.Mesh(
                new THREE.BoxGeometry(w, h, d),
                new THREE.MeshStandardMaterial({ color: color, roughness: 0.4 })
            );
            mesh.position.set(x, y, z);
            scene.add(mesh);
            obstacles.push({ mesh: mesh, box: new THREE.Box3().setFromObject(mesh) });
        }

        function createJumpPad(x, y, z) {
            const mesh = new THREE.Mesh(
                new THREE.CylinderGeometry(2, 2, 0.3, 16),
                new THREE.MeshStandardMaterial({ color: 0xfacc15, emissive: 0xd97706 })
            );
            mesh.position.set(x, y, z); scene.add(mesh); jumpPads.push(mesh);
        }

        function createPowerUp(x, y, z, type) {
            const color = type === 'health' ? 0x22c55e : 0xeab308;
            const mesh = new THREE.Mesh(
                new THREE.OctahedronGeometry(0.8),
                new THREE.MeshStandardMaterial({ color: color, emissive: color, roughness: 0.2 })
            );
            mesh.position.set(x, y, z); mesh.userData = { type: type, active: true, respawnTime: 0 };
            scene.add(mesh); powerUps.push(mesh);
        }

        function triggerSlide() {
            if (!isSliding && isGrounded) {
                isSliding = true; slideTimer = 0.45;
                pitchObject.position.y = -0.7;
            }
        }

        function triggerJump() {
            if (isGrounded) {
                velocityY = JUMP_FORCE; isGrounded = false; jumpCount = 1; playSound('jump');
            } else if (jumpCount === 1) {
                velocityY = JUMP_FORCE * 0.9; jumpCount = 2; playSound('jump');
            }
        }

        document.addEventListener('mousemove', (e) => {
            if (isMobile || document.pointerLockElement !== document.body) return;
            const sens = isAiming ? 0.0012 : 0.0022;
            yawObject.rotation.y -= e.movementX * sens;
            pitchObject.rotation.x -= e.movementY * sens;
            pitchObject.rotation.x = Math.max(-Math.PI / 2 + 0.1, Math.min(Math.PI / 2 - 0.1, pitchObject.rotation.x));
        });

        window.addEventListener('keydown', (e) => {
            keys[e.code] = true;
            if (['Digit1','Digit2','Digit3','Digit4','Digit5'].includes(e.code)) {
                switchWeapon(parseInt(e.code.replace('Digit','')) - 1);
            }
            if (e.code === 'KeyV') triggerPointerLockToggle();
            if (e.code === 'KeyC' || e.code === 'ShiftLeft') triggerSlide();
            if (e.code === 'Space') triggerJump();
        });
        window.addEventListener('keyup', (e) => { keys[e.code] = false; });

        function triggerPointerLockToggle() { togglePointerLock(); }

        window.addEventListener('mousedown', (e) => {
            if (!isMobile && document.pointerLockElement === document.body) {
                if (e.button === 0) shoot();
                if (e.button === 2) setAimingState(true);
            }
        });
        window.addEventListener('mouseup', (e) => {
            if (!isMobile && e.button === 2) setAimingState(false);
        });
        window.addEventListener('contextmenu', (e) => e.preventDefault());

        function setAimingState(aim) {
            isAiming = aim;
            targetFov = isAiming ? 45 : 75;
            document.getElementById('crosshair').classList.toggle('ads-active', isAiming);
        }

        const jZone = document.getElementById('joystick-zone');
        const jKnob = document.getElementById('joystick-knob');
        let jTouchId = null, lookTouchId = null;
        let jStart = { x: 0, y: 0 }, jVector = { x: 0, y: 0 };
        let lastTouchX = 0, lastTouchY = 0;

        document.getElementById('touch-controls').addEventListener('touchstart', e => {
            for (let touch of e.changedTouches) {
                const jRect = jZone.getBoundingClientRect();
                if (touch.clientX >= jRect.left && touch.clientX <= jRect.right &&
                    touch.clientY >= jRect.top && touch.clientY <= jRect.bottom && jTouchId === null) {
                    jTouchId = touch.identifier; jStart = { x: jRect.left + jRect.width / 2, y: jRect.top + jRect.height / 2 };
                    continue;
                }
                if (e.target.closest('#shoot-btn') || e.target.closest('#aim-btn') || e.target.closest('#jump-btn') || e.target.closest('#slide-btn') || e.target.closest('#weapon-selector')) {
                    continue;
                }
                if (lookTouchId === null) {
                    lookTouchId = touch.identifier; lastTouchX = touch.clientX; lastTouchY = touch.clientY;
                }
            }
        });

        document.getElementById('touch-controls').addEventListener('touchmove', e => {
            for (let touch of e.changedTouches) {
                if (touch.identifier === jTouchId) {
                    let dx = touch.clientX - jStart.x, dy = touch.clientY - jStart.y;
                    let dist = Math.hypot(dx, dy), maxDist = 40;
                    if (dist > maxDist) { dx = (dx / dist) * maxDist; dy = (dy / dist) * maxDist; }
                    jKnob.style.transform = `translate(${dx}px, ${dy}px)`;
                    jVector = { x: dx / maxDist, y: dy / maxDist };
                }
                if (touch.identifier === lookTouchId) {
                    let dx = touch.clientX - lastTouchX, dy = touch.clientY - lastTouchY;
                    lastTouchX = touch.clientX; lastTouchY = touch.clientY;
                    const sens = isAiming ? 0.0025 : 0.005;
                    yawObject.rotation.y -= dx * sens;
                    pitchObject.rotation.x -= dy * sens;
                    pitchObject.rotation.x = Math.max(-Math.PI / 2 + 0.1, Math.min(Math.PI / 2 - 0.1, pitchObject.rotation.x));
                }
            }
        });

        document.getElementById('touch-controls').addEventListener('touchend', e => {
            for (let touch of e.changedTouches) {
                if (touch.identifier === jTouchId) { jTouchId = null; jKnob.style.transform = `translate(0px, 0px)`; jVector = { x: 0, y: 0 }; }
                if (touch.identifier === lookTouchId) lookTouchId = null;
            }
        });

        document.getElementById('shoot-btn').addEventListener('touchstart', (e) => { e.preventDefault(); e.stopPropagation(); shoot(); });
        document.getElementById('aim-btn').addEventListener('touchstart', (e) => { e.preventDefault(); e.stopPropagation(); setAimingState(!isAiming); });
        document.getElementById('jump-btn').addEventListener('touchstart', (e) => { e.preventDefault(); e.stopPropagation(); triggerJump(); });
        document.getElementById('slide-btn').addEventListener('touchstart', (e) => { e.preventDefault(); e.stopPropagation(); triggerSlide(); });

        function switchWeapon(idx) {
            currentWepIdx = idx;
            document.querySelectorAll('.weapon-card').forEach((el, i) => el.classList.toggle('active', i === idx));
            updateFpsGunModel();
        }

        function triggerScreenShake(intensity) {
            pitchObject.rotation.x += (Math.random() - 0.5) * intensity;
            yawObject.rotation.y += (Math.random() - 0.5) * intensity;
        }

        function shoot() {
            const now = Date.now();
            const wep = WEAPONS[currentWepIdx];
            if (now - lastShootTime < wep.cooldown) return;
            lastShootTime = now;

            playSound(wep.name.toLowerCase());
            fpRecoil = 0.12;

            if (wep.isRocket) {
                const dir = new THREE.Vector3(); camera.getWorldDirection(dir);
                const rMesh = new THREE.Mesh(new THREE.SphereGeometry(0.3, 8, 8), new THREE.MeshBasicMaterial({ color: 0xf97316 }));
                rMesh.position.copy(yawObject.position); scene.add(rMesh);
                activeRockets.push({ mesh: rMesh, dir: dir, speed: 35, damage: wep.damage, life: 3.0 });
                return;
            }

            if (wep.isGrapple) {
                const raycaster = new THREE.Raycaster();
                raycaster.setFromCamera(new THREE.Vector2(0, 0), camera);
                const intersects = raycaster.intersectObjects(obstacles.map(o => o.mesh));
                if (intersects.length > 0) {
                    const hitPoint = intersects[0].point;
                    const pullDir = hitPoint.clone().sub(yawObject.position).normalize();
                    yawObject.position.add(pullDir.multiplyScalar(4)); velocityY = 6;
                }
                return;
            }

            const raycaster = new THREE.Raycaster();
            const spreadMult = isAiming ? 0.3 : 1.0;

            for (let i = 0; i < (wep.pellets || 1); i++) {
                raycaster.setFromCamera(new THREE.Vector2(0, 0), camera);
                raycaster.ray.direction.x += (Math.random() - 0.5) * wep.spread * spreadMult;
                raycaster.ray.direction.y += (Math.random() - 0.5) * wep.spread * spreadMult;

                const intersects = raycaster.intersectObjects(Object.values(otherMeshMap));
                if (intersects.length > 0) {
                    const hitObj = intersects[0].object;
                    playSound('hit'); triggerHitmarker();
                    
                    if (hitObj.userData.isDummy) {
                        hitObj.parent.position.y -= 0.1;
                    } else if (hitObj.userData.playerId) {
                        socket.emit('shoot_hit', { target_id: hitObj.userData.playerId, damage: wep.damage });
                    }
                }
            }
        }

        function triggerHitmarker() {
            const ch = document.getElementById('crosshair');
            ch.classList.add('hit-marker'); setTimeout(() => ch.classList.remove('hit-marker'), 100);
        }

        function createExplosion(pos) {
            triggerScreenShake(0.3);
            for (let i = 0; i < 15; i++) {
                const pMesh = new THREE.Mesh(new THREE.SphereGeometry(0.15, 4, 4), new THREE.MeshBasicMaterial({ color: 0xef4444 }));
                pMesh.position.copy(pos); scene.add(pMesh);
                particles.push({ mesh: pMesh, vel: new THREE.Vector3((Math.random()-0.5)*12, (Math.random()-0.5)*12, (Math.random()-0.5)*12), life: 0.4 });
            }
        }

        socket.on('init_player', (data) => {
            myId = data.id; players = data.players;
            for (let id in players) { if (id !== myId) players[id].meshGroup = createEnemyMesh(id, players[id].color); }
        });

        socket.on('player_joined', (pData) => { players[pData.id] = pData; players[pData.id].meshGroup = createEnemyMesh(pData.id, pData.color); });
        
        socket.on('player_moved', (pData) => {
            if (players[pData.id]?.meshGroup) {
                const anim = otherAnimMap[pData.id];
                anim.group.position.set(pData.x, pData.y - 0.9, pData.z);
                anim.group.rotation.y = pData.ry;
                
                const moveDist = Math.hypot(pData.x - (anim.lastX||pData.x), pData.z - (anim.lastZ||pData.z));
                if (moveDist > 0.01) {
                    const legAngle = Math.sin(Date.now() * 0.012) * 0.6;
                    anim.lLeg.rotation.x = legAngle;
                    anim.rLeg.rotation.x = -legAngle;
                } else {
                    anim.lLeg.rotation.x = 0; anim.rLeg.rotation.x = 0;
                }
                anim.lastX = pData.x; anim.lastZ = pData.z;
            }
        });

        socket.on('player_left', (id) => {
            if (players[id]?.meshGroup) {
                scene.remove(otherAnimMap[id].group);
                delete otherMeshMap[id]; delete otherAnimMap[id]; delete players[id];
            }
        });

        socket.on('player_damaged', (data) => {
            if (data.id === myId) {
                document.getElementById('healthFill').style.width = data.health + '%';
                const vig = document.getElementById('damage-vignette');
                vig.classList.add('active'); setTimeout(() => vig.classList.remove('active'), 200);
            }
        });

        socket.on('match_start', (data) => {
            inQueue = false;
            inBotMatch = !!data.isBot;

            document.getElementById('bot-btn').style.display = 'none';
            document.getElementById('locationTag').innerText = "LOCATION: ARENA";
            document.getElementById('locationTag').style.color = "#ef4444";
            document.getElementById('queue-status').innerText = inBotMatch ? "🤖 1v1 BOT MATCH IN PROGRESS" : "⚔️ 1v1 MATCH IN PROGRESS";
            document.getElementById('queue-status').style.borderColor = "#ef4444";
            document.getElementById('queue-status').style.color = "#ef4444";
            yawObject.position.set(data.spawnX, 2, data.spawnZ);

            if (inBotMatch) {
                activeBotMesh = createEnemyMesh('bot_1', 0xa855f7);
                activeBotMesh.position.set(data.botSpawnX, 0, data.botSpawnZ);
            }
        });

        socket.on('match_end', (data) => {
            inQueue = false;
            inBotMatch = false;

            if (activeBotMesh) {
                scene.remove(activeBotMesh);
                delete otherMeshMap['bot_1'];
                delete otherAnimMap['bot_1'];
                activeBotMesh = null;
            }

            const isWinner = (data.winner_id === myId);
            const overlay = document.getElementById('match-result-overlay');
            const resultTitle = document.getElementById('result-title');

            resultTitle.innerText = isWinner ? "VICTORY" : "DEFEAT";
            resultTitle.style.color = isWinner ? "#38bdf8" : "#ef4444";
            overlay.style.display = "flex";

            setTimeout(() => {
                overlay.style.display = "none";
                document.getElementById('bot-btn').style.display = 'block';
                document.getElementById('healthFill').style.width = '100%';
                document.getElementById('locationTag').innerText = "LOCATION: LOBBY";
                document.getElementById('locationTag').style.color = "#0284c7";
                document.getElementById('queue-status').innerText = "LOBBY PRACTICE AREA";
                document.getElementById('queue-status').style.borderColor = "#0284c7";
                document.getElementById('queue-status').style.color = "#0284c7";
                yawObject.position.set(0, 2, 100);
            }, 3000);
        });

        socket.on('kill_feed', (data) => {
            if (data.attacker === myId) players[myId].kills = (players[myId].kills || 0) + 1;
            else if (data.victim === myId) players[myId].deaths = (players[myId].deaths || 0) + 1;
            document.getElementById('scoreDisplay').innerText = `Kills: ${players[myId]?.kills || 0} | Deaths: ${players[myId]?.deaths || 0}`;
        });

        let clock = new THREE.Clock();

        function checkCollisions(newX, newZ) {
            const playerRadius = 0.6;

            // Lobby Circular Boundary Collision (Center at Z = 100, R = 29)
            if (!inBotMatch && yawObject.position.z > 50) {
                const distToCenter = Math.hypot(newX, newZ - 100);
                if (distToCenter > 29) return true;
            }

            for (let obs of obstacles) {
                if (newX + playerRadius > obs.box.min.x && newX - playerRadius < obs.box.max.x &&
                    newZ + playerRadius > obs.box.min.z && newZ - playerRadius < obs.box.max.z &&
                    yawObject.position.y < obs.box.max.y) return true;
            }
            return false;
        }

        function updateBotAI(delta) {
            if (!inBotMatch || !activeBotMesh) return;

            const bPos = activeBotMesh.position;
            const pPos = yawObject.position;
            const dx = pPos.x - bPos.x;
            const dz = pPos.z - bPos.z;
            const dist = Math.hypot(dx, dz);

            // Dynamic Strafe Timer & Direction Switch
            botStrafeTimer -= delta;
            if (botStrafeTimer <= 0) {
                botStrafeTimer = 0.8 + Math.random() * 1.2;
                botStrafeDir = Math.random() < 0.5 ? 1 : -1;
            }

            // Random Jumping AI
            botJumpTimer -= delta;
            if (botJumpTimer <= 0 && Math.random() < 0.4) {
                botJumpTimer = 1.5 + Math.random() * 2.5;
                botYVelocity = JUMP_FORCE;
            }

            // Apply Bot Physics Grounding
            botYVelocity += GRAVITY * delta;
            bPos.y += botYVelocity * delta;
            if (bPos.y <= 0) { bPos.y = 0; botYVelocity = 0; }

            // Movement Vector (Forward + Tactical Strafe)
            const forwardX = dx / dist;
            const forwardZ = dz / dist;
            const strafeX = -forwardZ * botStrafeDir;
            const strafeZ = forwardX * botStrafeDir;

            let moveSpeed = 10.5;
            bPos.x += (forwardX * 0.4 + strafeX * 0.8) * moveSpeed * delta;
            bPos.z += (forwardZ * 0.4 + strafeZ * 0.8) * moveSpeed * delta;

            // Compact Boundary Constraint for Bot
            bPos.x = Math.max(-32, Math.min(32, bPos.x));
            bPos.z = Math.max(-32, Math.min(32, bPos.z));

            // Trick-Shot Logic vs Normal Aiming
            const now = Date.now();
            if (botTrickshotState === 1) {
                activeBotMesh.rotation.y += delta * 20; // 360 Spin
                if (now - botLastShootTime > 350) {
                    botTrickshotState = 0;
                    playSound('sniper');
                    socket.emit('bot_shoot_player', { damage: 45 });
                }
            } else {
                activeBotMesh.rotation.y = Math.atan2(dx, dz);

                if (dist < 35 && now - botLastShootTime > 900) {
                    botLastShootTime = now;
                    
                    // 25% Chance to Perform a 360 Trick-Shot
                    if (Math.random() < 0.25) {
                        botTrickshotState = 1;
                    } else {
                        playSound('rifle');
                        socket.emit('bot_shoot_player', { damage: 16 });
                    }
                }
            }
        }

        function animate() {
            requestAnimationFrame(animate);
            const delta = clock.getDelta();

            updateBotAI(delta);

            // Teleporter Ring Animation
            if (teleporterRingMesh) teleporterRingMesh.rotation.z += delta * 1.5;

            // Target Dummies Bobbing Animation
            targetDummies.forEach(td => {
                td.group.position.y = td.baseY + Math.sin(Date.now() * 0.003) * 0.15;
            });

            currentFov += (targetFov - currentFov) * 0.15;
            camera.fov = currentFov; camera.updateProjectionMatrix();

            if (isSliding) {
                slideTimer -= delta;
                if (slideTimer <= 0) { isSliding = false; pitchObject.position.y = 0; }
            }

            if (speedBoostTime > 0) {
                speedBoostTime -= delta;
                document.getElementById('buffDisplay').innerText = `⚡ SPEED OVERDRIVE (${Math.ceil(speedBoostTime)}s)`;
                if (speedBoostTime <= 0) document.getElementById('buffDisplay').innerText = "";
            }

            powerUps.forEach(p => {
                p.rotation.y += delta * 2;
                if (p.userData.active && yawObject.position.distanceTo(p.position) < 1.8) {
                    p.userData.active = false; p.visible = false; p.userData.respawnTime = 10;
                    if (p.userData.type === 'health') socket.emit('heal_player', { amount: 50 });
                    else if (p.userData.type === 'speed') speedBoostTime = 5;
                } else if (!p.userData.active) {
                    p.userData.respawnTime -= delta;
                    if (p.userData.respawnTime <= 0) { p.userData.active = true; p.visible = true; }
                }
            });

            jumpPads.forEach(pad => {
                if (Math.hypot(yawObject.position.x - pad.position.x, yawObject.position.z - pad.position.z) < 2.0 && yawObject.position.y <= 2.2) {
                    velocityY = JUMP_FORCE * 1.8; isGrounded = false; playSound('jump');
                }
            });

            for (let i = activeRockets.length - 1; i >= 0; i--) {
                const r = activeRockets[i];
                r.mesh.position.add(r.dir.clone().multiplyScalar(r.speed * delta));
                r.life -= delta;

                let hitTarget = null;
                for (let id in otherMeshMap) {
                    if (r.mesh.position.distanceTo(otherMeshMap[id].position) < 1.5) { hitTarget = id; break; }
                }

                if (hitTarget || checkCollisions(r.mesh.position.x, r.mesh.position.z) || r.life <= 0) {
                    createExplosion(r.mesh.position); playSound('rocket');
                    if (hitTarget && !hitTarget.startsWith('dummy')) socket.emit('shoot_hit', { target_id: hitTarget, damage: r.damage });
                    scene.remove(r.mesh); activeRockets.splice(i, 1);
                }
            }

            for (let i = particles.length - 1; i >= 0; i--) {
                const pt = particles[i];
                pt.mesh.position.add(pt.vel.clone().multiplyScalar(delta));
                pt.life -= delta;
                if (pt.life <= 0) { scene.remove(pt.mesh); particles.splice(i, 1); }
            }

            if (isMobile || document.pointerLockElement === document.body) {
                let moveSpeed = isSliding ? 22 : (speedBoostTime > 0 ? 18 : (isAiming ? 8 : 12));
                let moveX = 0, moveZ = 0;

                if (isMobile) {
                    moveX = jVector.x; moveZ = jVector.y;
                } else {
                    if (keys['KeyW']) moveZ -= 1;
                    if (keys['KeyS']) moveZ += 1;
                    if (keys['KeyA']) moveX -= 1;
                    if (keys['KeyD']) moveX += 1;
                    if (moveX !== 0 || moveZ !== 0) { const len = Math.hypot(moveX, moveZ); moveX /= len; moveZ /= len; }
                }

                const sinYaw = Math.sin(yawObject.rotation.y), cosYaw = Math.cos(yawObject.rotation.y);
                const vx = (moveX * cosYaw + moveZ * sinYaw) * moveSpeed * delta;
                const vz = (moveZ * cosYaw - moveX * sinYaw) * moveSpeed * delta;

                if (!checkCollisions(yawObject.position.x + vx, yawObject.position.z)) yawObject.position.x += vx;
                if (!checkCollisions(yawObject.position.x, yawObject.position.z + vz)) yawObject.position.z += vz;

                velocityY += GRAVITY * delta;
                yawObject.position.y += velocityY * delta;

                if (yawObject.position.y <= 2) { yawObject.position.y = 2; velocityY = 0; isGrounded = true; jumpCount = 0; }

                const wepInfo = WEAPONS[currentWepIdx];
                const targetPos = isAiming ? wepInfo.adsPos : wepInfo.hipPos;

                if (moveX !== 0 || moveZ !== 0) {
                    fpBobTimer += delta * 12;
                } else {
                    fpBobTimer += delta * 3;
                }

                const bobX = Math.sin(fpBobTimer) * (isAiming ? 0.003 : 0.015);
                const bobY = Math.cos(fpBobTimer * 2) * (isAiming ? 0.003 : 0.015);

                fpRecoil = THREE.MathUtils.lerp(fpRecoil, 0, 0.15);

                fpRigGroup.position.x += (targetPos[0] + bobX - fpRigGroup.position.x) * 0.2;
                fpRigGroup.position.y += (targetPos[1] + bobY - fpRigGroup.position.y) * 0.2;
                fpRigGroup.position.z += (targetPos[2] + fpRecoil - fpRigGroup.position.z) * 0.2;

                // Queue Teleporter Pad Entrance
                if (Math.hypot(yawObject.position.x, yawObject.position.z - 86) < 4.5 && !inQueue && !inBotMatch) {
                    inQueue = true; socket.emit('enter_queue');
                    document.getElementById('queue-status').innerText = "WAITING FOR OPPONENT...";
                    document.getElementById('queue-status').style.borderColor = "#facc15";
                    document.getElementById('queue-status').style.color = "#facc15";
                }

                socket.emit('player_update', { x: yawObject.position.x, y: yawObject.position.y, z: yawObject.position.z, ry: yawObject.rotation.y });
            }

            renderer.render(scene, camera);
        }

        function onWindowResize() {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        }

        init3D(); animate();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('connect')
def handle_connect():
    p_id = request.sid
    PLAYERS[p_id] = {
        'id': p_id,
        'x': 0, 'y': 2, 'z': 100, 'ry': 0,
        'health': 100, 'kills': 0, 'deaths': 0, 'color': 0xef4444
    }
    emit('init_player', {'id': p_id, 'players': PLAYERS}, room=p_id)
    emit('player_joined', PLAYERS[p_id], broadcast=True, include_self=False)

@socketio.on('set_color')
def handle_set_color(data):
    p_id = request.sid
    if p_id in PLAYERS:
        PLAYERS[p_id]['color'] = data.get('color', 0xef4444)

@socketio.on('heal_player')
def handle_heal_player(data):
    p_id = request.sid
    if p_id in PLAYERS:
        PLAYERS[p_id]['health'] = min(100, PLAYERS[p_id]['health'] + data.get('amount', 50))
        emit('player_damaged', {'id': p_id, 'health': PLAYERS[p_id]['health']}, room=p_id)

@socketio.on('disconnect')
def handle_disconnect():
    p_id = request.sid
    if p_id in PLAYERS:
        del PLAYERS[p_id]
        if p_id in QUEUE: QUEUE.remove(p_id)
        if p_id in MATCHES:
            opponent = MATCHES[p_id]
            if opponent in PLAYERS: emit('match_end', {'winner_id': opponent}, room=opponent)
            del MATCHES[p_id]
        if p_id in BOT_MATCHES:
            del BOT_MATCHES[p_id]
        emit('player_left', p_id, broadcast=True)

@socketio.on('enter_queue')
def handle_enter_queue():
    p_id = request.sid
    if p_id not in QUEUE: QUEUE.append(p_id)
    if len(QUEUE) >= 2:
        p1, p2 = QUEUE.pop(0), QUEUE.pop(0)
        MATCHES[p1] = p2; MATCHES[p2] = p1
        emit('match_start', {'spawnX': -15, 'spawnZ': 0, 'isBot': False}, room=p1)
        emit('match_start', {'spawnX': 15, 'spawnZ': 0, 'isBot': False}, room=p2)

@socketio.on('start_bot_match')
def handle_start_bot_match():
    p_id = request.sid
    if p_id in QUEUE: QUEUE.remove(p_id)
    
    BOT_MATCHES[p_id] = {'bot_health': 100}
    emit('match_start', {
        'spawnX': -15, 'spawnZ': 0, 
        'botSpawnX': 15, 'botSpawnZ': 0, 
        'isBot': True
    }, room=p_id)

@socketio.on('bot_shoot_player')
def handle_bot_shoot(data):
    p_id = request.sid
    damage = data.get('damage', 15)
    if p_id in PLAYERS:
        PLAYERS[p_id]['health'] -= damage
        if PLAYERS[p_id]['health'] <= 0:
            PLAYERS[p_id]['health'] = 100
            PLAYERS[p_id]['deaths'] += 1
            if p_id in BOT_MATCHES: del BOT_MATCHES[p_id]
            emit('match_end', {'winner_id': 'bot_1', 'loser_id': p_id}, room=p_id)
            emit('kill_feed', {'attacker': 'bot_1', 'victim': p_id}, broadcast=True)
        else:
            emit('player_damaged', {'id': p_id, 'health': PLAYERS[p_id]['health']}, room=p_id)

@socketio.on('player_update')
def handle_player_update(data):
    p_id = request.sid
    if p_id in PLAYERS:
        PLAYERS[p_id]['x'] = data.get('x', 0)
        PLAYERS[p_id]['y'] = data.get('y', 2)
        PLAYERS[p_id]['z'] = data.get('z', 100)
        PLAYERS[p_id]['ry'] = data.get('ry', 0)
        emit('player_moved', PLAYERS[p_id], broadcast=True, include_self=False)

@socketio.on('shoot_hit')
def handle_shoot_hit(data):
    target_id = data.get('target_id')
    damage = data.get('damage', 20)
    attacker_id = request.sid

    # Handling Bot Targets
    if target_id == 'bot_1' and attacker_id in BOT_MATCHES:
        bot = BOT_MATCHES[attacker_id]
        bot['bot_health'] -= damage
        if bot['bot_health'] <= 0:
            if attacker_id in PLAYERS:
                PLAYERS[attacker_id]['kills'] += 1
                PLAYERS[attacker_id]['health'] = 100
            del BOT_MATCHES[attacker_id]
            emit('match_end', {'winner_id': attacker_id, 'loser_id': 'bot_1'}, room=attacker_id)
            emit('kill_feed', {'attacker': attacker_id, 'victim': 'bot_1'}, broadcast=True)
        return

    # Handling Human Targets
    if target_id in PLAYERS:
        target = PLAYERS[target_id]
        target['health'] -= damage
        
        if target['health'] <= 0:
            target['health'] = 100
            target['deaths'] += 1
            if attacker_id in PLAYERS:
                PLAYERS[attacker_id]['kills'] += 1
                PLAYERS[attacker_id]['health'] = 100

            emit('match_end', {'winner_id': attacker_id, 'loser_id': target_id}, room=target_id)
            emit('match_end', {'winner_id': attacker_id, 'loser_id': target_id}, room=attacker_id)
            emit('kill_feed', {'attacker': attacker_id, 'victim': target_id}, broadcast=True)

            if target_id in MATCHES: del MATCHES[target_id]
            if attacker_id in MATCHES: del MATCHES[attacker_id]
        else:
            emit('player_damaged', {'id': target_id, 'health': target['health']}, broadcast=True)

if __name__ == '__main__':
    ip = get_local_ip()
    port = 5000
    print(f"==================================================")
    print(f"🎮 Daytime FPS Arena Live On: http://{ip}:{port}")
    print(f"==================================================")
    socketio.run(app, host='0.0.0.0', port=port)
