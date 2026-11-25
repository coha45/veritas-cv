import { useState } from "react"
import { clsx } from "clsx"
import { Link } from "react-router-dom"
import { FaArrowRightLong } from "react-icons/fa6";
import { FaX } from "react-icons/fa6";
import { MdDashboard } from "react-icons/md";
import { MdOutlinePayment } from "react-icons/md";
import { FaDatabase } from "react-icons/fa6";
import { FaRegEye } from "react-icons/fa";

import logo from "../assets/logo.svg"

const btnLinks = [
    { 
        title : "Dashboard", 
        url : "/dashboard",
        icon : <MdDashboard color="white" />
    },
    {
        title : "Top-Down View",
        url : "/top-down",
        icon : <FaRegEye />
    },
    {
        title : "Payments",
        url : "/payments",
        icon : <MdOutlinePayment />
    }, 
    {
        title : "Database",
        url : "/view-data",
        icon : <FaDatabase /> 
    }
]

const Sidebar = () => {
  const [active, setActive] = useState(false)

  return (
    <aside className={clsx("min-h-screen p-2 h-full bg-white shadow-gray-400 shadow-md flex flex-col gap-4 items-center",
        active && "w-50",
        !active && "w-fit"
    )}>
        <div className="flex flex-col justify-center items-center gap-2">
            <button
                onClick={() => setActive(prev => !prev)} 
                className="btn btn-circle self-end"
            >
                {
                    !active ?
                    <FaArrowRightLong /> : 
                    <FaX />

                }
            </button>
            {
                active &&
                <img src={logo} className="h-30 w-full" />
            }
        </div>
        {
            active &&
            <ul className="flex flex-col justify-center items-center gap-2 w-full">
                {
                    btnLinks.map((btn) => (
                        <li className="w-full">
                            <Link to={btn.url}>
                                <button 
                                    className="cursor-pointer btn btn-block btn-neutral"
                                >   
                                    {btn.icon}
                                    { btn.title }
                                </button>
                            </Link>
                        </li>
                    ))
                }
            </ul>
        }
    </aside>
  )
}

export default Sidebar