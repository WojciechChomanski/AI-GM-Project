const openai = process.env.OPENAI_API_KEY ? new (require('openai'))({apiKey:process.env.OPENAI_API_KEY}) : null;
module.exports.chat = async ({message,context})=>{
  if(!openai) return {reply:`Stub: "${message}"`};
  const completion = await openai.chat.completions.create({
    model:'gpt-4o-mini',
    messages:[{role:'user',content:message}]
  });
  return {reply:completion.choices[0].message.content};
};