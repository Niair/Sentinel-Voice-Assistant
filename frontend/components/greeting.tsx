import { motion } from "framer-motion";

export const Greeting = () => {
  return (
    <div
      className="mx-auto mt-4 flex size-full max-w-3xl flex-col justify-center px-4 md:mt-16 md:px-8"
      key="overview"
    >
      <motion.div
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col gap-2"
        exit={{ opacity: 0, scale: 0.95 }}
        initial={{ opacity: 0, y: 20 }}
        transition={{ delay: 0.2, type: "spring", stiffness: 100 }}
      >
        <h1 className="text-4xl md:text-6xl font-bold tracking-tight bg-gradient-to-br from-foreground to-foreground/50 bg-clip-text text-transparent">
          I'm Sentinel.
        </h1>
        <p className="text-2xl md:text-3xl font-medium text-muted-foreground/80 tracking-tight">
          How can I assist your workflow today?
        </p>
      </motion.div>
    </div>
  );
};
