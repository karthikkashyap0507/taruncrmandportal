"use client";

import { motion } from "framer-motion";

interface ImpactStatProps {
  value: number;
  suffix: string;
  label: string;
  isDecimal?: boolean;
  index?: number;
}

export function ImpactStat({ value, suffix, label, isDecimal, index = 0 }: ImpactStatProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay: index * 0.1 }}
      className="glass-card p-6 text-center"
    >
      <p className="text-3xl font-bold gradient-text sm:text-4xl">
        {isDecimal ? value : value}
        {suffix}
      </p>
      <p className="mt-2 text-sm text-[#94A3B8]">{label}</p>
    </motion.div>
  );
}
