import React from 'react'

const Page = ({ children }) => {
  return (
    <section className="p-10 w-full min-h-screen">
        { children }
    </section>
  )
}

export default Page