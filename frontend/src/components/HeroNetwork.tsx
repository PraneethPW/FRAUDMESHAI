import { Line, OrbitControls, Sphere } from '@react-three/drei'
import { Canvas, useFrame } from '@react-three/fiber'
import { useMemo, useRef } from 'react'
import type { Group } from 'three'

const positions: [number, number, number][] = [[-3,1.4,0],[-1.5,-.4,.7],[.2,1.1,-.3],[1.4,-1,.2],[3,.9,-.7],[2.6,-2,-.3],[-2.8,-1.7,-.4],[0,-2,1]]

function Mesh() {
  const group = useRef<Group>(null)
  const reduce = useMemo(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches, [])
  useFrame(({ clock, pointer }) => {
    if (!group.current || reduce) return
    group.current.rotation.y = clock.elapsedTime * .035 + pointer.x * .08
    group.current.rotation.x += (pointer.y * .04 - group.current.rotation.x) * .02
  })
  return <group ref={group}>
    {positions.map((point, index) => <group key={index}>
      <Sphere args={[index === 3 ? .22 : .11, 24, 24]} position={point}>
        <meshStandardMaterial color={index === 3 ? '#ff5578' : '#9b7cff'} emissive={index === 3 ? '#ff224f' : '#6f39ff'} emissiveIntensity={3} toneMapped={false} />
      </Sphere>
      {index < positions.length - 1 && <Line points={[point, positions[(index + 1) % positions.length]]} color={index === 2 || index === 3 ? '#ff5578' : '#6e55af'} lineWidth={.55} transparent opacity={.68} />}
      {index % 2 === 0 && <Line points={[point, positions[(index + 3) % positions.length]]} color="#2c88d9" lineWidth={.35} transparent opacity={.45} />}
    </group>)}
  </group>
}

export default function HeroNetwork() {
  return <Canvas camera={{ position: [0, 0, 7], fov: 48 }} dpr={[1, 1.5]} gl={{ antialias: true, alpha: true }}>
    <ambientLight intensity={.35} />
    <pointLight position={[1, 2, 4]} intensity={8} color="#7455ff" />
    <Mesh />
    <OrbitControls enableZoom={false} enablePan={false} enableRotate={false} />
  </Canvas>
}

