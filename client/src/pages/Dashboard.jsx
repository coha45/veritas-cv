import React from 'react'
import Page from './Page'
import LeanbotTable from '../components/LeanbotTable'
import { data } from '../data'
import { useVeritas } from '../context/VeritasContext'
import Camera from '../components/Camera'
import CameraFeed from '../components/CameraFeed'

const Dashboard = () => {
    const {
        leanbots,
        trafficState,
        connected,
        frames
    } = useVeritas()

    return (
        <Page>
            <h1 className="font-bold text-5xl">VERITAS Dashboard</h1>
            <section className="flex flex-col gap-5 mt-5">
                <CameraFeed frames={frames} />
                {
                    leanbots.length >= 1 ?
                    <LeanbotTable data={leanbots} /> :
                    <h1 className="text-center italic text-gray-400">No Cars Detected...</h1>
                }
            </section>        
        </Page>
    )
}

export default Dashboard